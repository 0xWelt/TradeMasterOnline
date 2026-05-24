# MARL 框架调研：参考案例

本文展示 deep-survey 方法论在多智能体强化学习（MARL）框架调研中的具体应用。可作为调研 MARL 或结构相似领域（仿真环境、游戏引擎、多智能体系统）时的参考。

## 1. 范围

源码级调研 10+ 个 MARL 框架。输出：结构化报告，含形式化模型分析、源码级框架分析、对比矩阵、以及面向金融交易环境的领域建议。

## 2. 来源选择

| 优先级 | 框架 | 角色 |
|---|---|---|
| P0 | PettingZoo | 标准 AEC/Parallel API |
| P0 | RLlib | 生产级 MARL（Ray） |
| P0 | OpenSpiel | 扩展式博弈 / 博弈论 |
| P1 | SMACv2 | 星际争霸基准 |
| P1 | Melting Pot | 社会困境 |
| P1 | VMAS | 向量化多智能体物理仿真 |
| P2 | MARLlib | 算法库 |
| P2 | BenchMARL | 基准测试框架 |
| P2 | JAXMARL | JAX 加速 MARL |
| P3 | ABIDES-MARL | 金融限价订单簿仿真 |

## 3. 形式化模型辨析

### 层级关系

```
POSG（部分可观测随机博弈，最一般）
├── Markov Game / Stochastic Game（完全可观测）
│   └── MDP（单智能体 + 完全可观测）
├── Dec-POMDP（完全合作 + 部分可观测，共享奖励）
│   └── MMDP（完全合作 + 完全可观测）
├── POMDP（单智能体 + 部分可观测）
└── AEC Game（PettingZoo，序贯 stepping，与 POSG 数学等价）
    ≈ EFG + 每步奖励 + 内建环境动态
```

### 关键区别

| 模型 | 智能体数 | 可观测性 | 奖励 | 核心难点 |
|---|---|---|---|---|
| MDP | 1 | 完全 | 单个 | 无 |
| POMDP | 1 | 部分 | 单个 | Belief 更新 |
| Markov Game | N≥2 | 完全 | 各自独立 | 均衡求解 |
| POSG | N≥2 | 部分 | 各自独立 | 交互不确定性 + Belief |
| Dec-POMDP | N≥2 | 部分 | **共享** | 无通信协调 |
| EFG | N≥2 | 部分 | 各自独立 | 博弈树巨大，仅终端奖励 |
| AEC | N≥2 | 部分 | 各自独立 | 序贯 stepping 语义 |

### 常见错误纠正

- **错误**："Dec-POMDP 是单智能体的。" **正确**：它是多智能体的，是完全合作的 POSG，所有智能体共享奖励。
- **错误**："AEC 是一种 EFG。" **正确**：AEC 与 EFG 相似（都是序贯），但增加了环境智能体和每步奖励。AEC ⟺ POSG 数学等价。
- **错误**："Markov Game 和 Stochastic Game 不同。" **正确**：同一模型，不同命名习惯（博弈论 vs 计算机科学）。

## 4. 对比维度（10 个）

1. 形式化模型（POSG / EFG / AEC / 自定义）
2. API 风格（AEC 序贯 / Parallel 同时 / State-centric）
3. 观测语义（观测 vs 信息集 vs 全局状态）
4. 动作空间（离散 / 连续 / 混合 / 动作掩码）
5. 奖励时机（每步 / 周期结束 / 终端 / 延迟归因）
6. 动态智能体（固定 / 出生死亡 / 可变数量）
7. 向量化（无 / CPU 批处理 / GPU / JAX jit）
8. 异构支持（同构共享 / 异构独立 / 分组策略）
9. 不完全信息建模（信息集、随机观测、私有状态）
10. 领域示例（棋类 / 物理 / 社会困境 / 金融 / 游戏）

## 5. 源码级发现

### PettingZoo AEC

- `AECEnv` / `ParallelEnv` 是两种并行抽象，共同父类只有 `object`
- `agent_iter()` 是遍历 `agent_selection` 的生成器，不推进环境
- `_was_dead_step()` 通过跳过死亡智能体处理生命周期
- `possible_agents` 是静态上限；`agents` 是动态存活列表
- `parallel_to_aec_wrapper` 缓存动作直到 `_agent_selector.is_last()` 再调用并行 step

### OpenSpiel

- `State` + `Game` 分离：`Game` 定义规则，`State` 表示具体局面
- `CurrentPlayer()` 对随机转移返回 `kChancePlayer`
- `InformationState()` vs `Observation()`：前者用于完美回忆，后者用于 RL
- CFR / MCCFR 在信息集上运算，而非原始状态

### RLlib

- `MultiAgentEnv` 基于 POSG：`step(actions_dict)` 同时 stepping
- `MultiAgentBatch` 处理异构 episode 长度
- `PolicyMap` 支持运行时策略切换

### Melting Pot

- Substrate（物理引擎）+ Scenario（社会配置）+ Bot（背景）三层设计
- `FocalPerCapitaReturn` 用于社会困境评估
- `_await_full_action` 异步合并 focal + bot 动作

## 6. 金融领域适配

| 金融特性 | MARL 概念 | 检查项 |
|---|---|---|
| 限价订单簿（LOB）仿真 | 状态空间设计 | 是否有连续/高维状态示例？ |
| 序贯撮合 | AEC 序贯 stepping | 是否原生支持 AEC API？ |
| 异构参与者（知情/噪声/做市商） | 异构/分组策略 | `share_policy` 粒度？ |
| 涨跌停 / 停牌 | 动作掩码（`action_mask`） | 观测空间是否支持 Dict？ |
| 延迟盈亏归因 | `_cumulative_rewards` | 是否支持延迟奖励计算？ |
| 账户开户/销户 | 动态智能体 | `possible_agents` 机制？ |
| 市场冲击 / 宏观新闻 | Chance Node | 环境是否有随机事件注入？ |
| 批量回测 | 向量化 / `reset_at` | 是否支持单独重置某环境？ |

**关键发现**：ABIDES-MARL（ETH Zurich / JPMorgan 背景）是目前最专业的金融 MARL 环境，支持 LOB 仿真和异构智能体。采用前需评估维护状态。

## 7. 交易环境设计建议

1. 采用 PettingZoo AEC API 表达序贯撮合语义
2. 采用 VMAS 式向量化支持批量回测
3. 采用 Melting Pot 的 Substrate/Scenario 双层架构（市场微结构 + 参与者配置）
4. 用 OpenSpiel 的信息集建模不完全信息
5. 用 `action_mask` 处理涨跌停和停牌约束
6. 用 `_cumulative_rewards` 处理延迟盈亏归因
7. 用 `possible_agents` 管理账户生命周期
