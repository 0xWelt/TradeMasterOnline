# 多智能体强化学习环境框架深度调研报告

> 创建日期：2026-05-24
>
> 调研目标：为 TradeMasterOnline 的交易模拟环境设计提供参考，深入理解现有 MARL Env 框架的设计理念、API 模式、架构取舍与源码实现细节。
>
> 本报告基于各框架 **master/main 分支的实际源代码阅读**，辅以官方文档和论文。所有代码片段均来自真实仓库文件。

---

## 目录

- [1. 概述](#1-概述)
- [2. 核心形式化模型对比](#2-核心形式化模型对比)
  - [2.1 Agent Environment Cycle (AEC)](#21-agent-environment-cycle-aec)
  - [2.2 Partially Observable Stochastic Game (POSG)](#22-partially-observable-stochastic-game-posg)
  - [2.3 Extensive-Form Game (EFG)](#23-extensive-form-game-efg)
- [3. 各框架深度分析](#3-各框架深度分析)
  - [3.1 PettingZoo](#31-pettingzoo)
  - [3.2 MARLlib + RLlib](#32-marllib--rllib)
  - [3.3 Melting Pot](#33-melting-pot)
  - [3.4 OpenSpiel](#34-openspiel)
  - [3.5 BenchMARL](#35-benchmarl)
  - [3.6 VMAS](#36-vmas)
  - [3.7 SMACv2](#37-smacv2)
  - [3.8 JAXMARL](#38-jaxmarl)
  - [3.9 补充框架概览](#39-补充框架概览)
- [4. 金融领域 MARL 环境专项发现](#4-金融领域-marl-环境专项发现)
- [5. 横向对比分析](#5-横向对比分析)
- [6. 对 TradeMasterOnline 的设计建议](#6-对-trademasteronline-的设计建议)
- [7. 参考资料](#7-参考资料)

---

## 1. 概述

多智能体强化学习（Multi-Agent Reinforcement Learning, MARL）环境框架是连接智能体策略与环境动态的桥梁。一个好的 MARL 环境框架需要同时解决以下挑战：

1. **通用性**：支持合作、竞争、混合等多种博弈模式
2. **动态性**：支持智能体的生成与消亡、数量变化
3. **时序性**：支持回合制（turn-based）和同时行动（simultaneous-move）
4. **信息结构**：支持完全/不完全信息、局部/全局观测
5. **可扩展性**：向量化执行、大规模并行采样
6. **生态兼容**：与主流训练框架（PyTorch、Ray、JAX）无缝集成

本报告对当前最具影响力的 **10+ 个 MARL 环境/训练框架**进行深度源码级调研，覆盖从 API 标准层（PettingZoo）、训练框架层（MARLlib、RLlib、BenchMARL）、物理仿真层（VMAS、SMACv2、JAXMARL）到博弈论基础层（OpenSpiel、Melting Pot）的完整技术栈。此外，报告还专项调研了**金融领域现有的 MARL 仿真环境**（ABIDES-MARL 等）。

---

## 2. 核心形式化模型对比

在深入各框架之前，有必要先理解三种形式化模型——这是所有 MARL 环境 API 设计的理论基础。

### 2.1 Agent Environment Cycle (AEC)

**提出者**：[PettingZoo](https://github.com/Farama-Foundation/PettingZoo) 团队（论文 [arXiv:2009.14471](https://arxiv.org/abs/2009.14471)）

AEC 将多智能体交互建模为**智能体-环境循环序列**。在任意时刻，只有一个"活跃智能体"与环境交互：

```
Env -> selects agent i -> agent i observes & acts -> Env updates -> Env selects next agent j
```

这类似于操作系统中的进程调度器：环境是调度器，智能体是进程，每次只有一个进程获得 CPU 时间片。

**为什么不用 POSG？** PettingZoo 论文指出：
- POSG 假设所有智能体同时行动，难以自然表达回合制游戏（如象棋、扑克）
- POSG 的奖励归因模糊，易导致实现层面的 race condition 和 bug
- 基于 POSG 的 MARL 实现中曾存在长期未发现的奖励归因错误，导致学习效果下降超过 22%

**AEC 与 POSG 的等价性**：论文证明了任何 AEC 游戏都可以表示为 POSG，反之亦然。AEC 在表达能力上不弱于 POSG，但在实现层面更加清晰。

### 2.2 Partially Observable Stochastic Game (POSG)

POSG 是单智能体 POMDP 的直接扩展：

$$(S, \{A_i\}, P, \{R_i\}, \{O_i\}, \gamma, N)$$

其中每个智能体有自己的动作空间 $A_i$、奖励函数 $R_i$ 和观测函数 $O_i$。状态转移 $P(s' \mid s, a_1, \dots, a_N)$ 依赖所有智能体的联合动作。

**代表实现**：[RLlib](https://docs.ray.io/en/latest/rllib/index.html) 的 `MultiAgentEnv` 直接基于 POSG 模型，所有智能体同时行动，`step(actions_dict)` 接收联合动作字典。

### 2.3 Extensive-Form Game (EFG)

EFG 将博弈表示为**一棵博弈树**：

```
博弈树节点 = 状态（State）
    ├── 玩家节点：智能体选择动作
    ├── 机会节点（Chance Node）：环境按概率采样（如发牌、骰子）
    └── 终止节点：收益向量（每个智能体的奖励）
```

**代表实现**：[OpenSpiel](https://github.com/google-deepmind/open_spiel) 完全基于 EFG。关键概念是**信息集（Information Set）**：在不完美信息游戏中，玩家无法区分的历史节点集合。

### 三种模型的对应关系

| 概念 | AEC (PettingZoo) | POSG (RLlib) | EFG (OpenSpiel) |
|------|------------------|--------------|-----------------|
| 核心抽象 | `agent_iter()` 生成器 | 联合动作字典 | 博弈树节点 `State` |
| 时序表达 | 自然（顺序步进） | 需额外处理回合制 | 自然（树遍历） |
| 同时行动 | `ParallelEnv` 包装器 | 原生支持 | `SimultaneousNode` |
| 不完全信息 | 通过局部观测模拟 | 通过局部观测模拟 | **信息集（Information Set）**原生支持 |
| 机会/随机性 | 环境内部处理 | 环境内部处理 | `ChanceNode` 显式建模 |
| 智能体动态变化 | `agents` 动态列表 | 需手动管理 | 需手动管理 |

---

## 3. 各框架深度分析


### 3.1 PettingZoo

**项目信息**
| 属性 | 内容 |
|------|------|
| 组织 | [Farama Foundation](https://farama.org/) |
| 定位 | 多智能体环境标准化 API + 参考环境集合 |
| 核心论文 | [*PettingZoo: Gym for Multi-Agent Reinforcement Learning*](https://arxiv.org/abs/2009.14471) (2020) |
| 官方文档 | [pettingzoo.farama.org](https://pettingzoo.farama.org/) |
| GitHub | [Farama-Foundation/PettingZoo](https://github.com/Farama-Foundation/PettingZoo) |
| 维护状态 | 活跃，Gymnasium 生态官方多智能体标准 |

#### 3.1.1 核心类图与继承关系

PettingZoo 的架构可以抽象为两条主线：**AEC API** 与 **Parallel API**。

```text
gymnasium.Env (single-agent)
    │
    ├─> (独立扩展) ───────────────────────────────┐
    │                                              │
AECEnv (pettingzoo.utils.env)                ParallelEnv (pettingzoo.utils.env)
    │                                              │
    ├─> BaseWrapper (pettingzoo.utils.wrappers.base)  ├─> BaseParallelWrapper
    │       │                                              │
    │       ├─> OrderEnforcingWrapper                      │
    │       │       │                                      │
    │       │       └─> (SuperSuit) BaseWrapper            │
    │       │               │                              │
    │       ├─> TerminateIllegalWrapper                    │
    │       ├─> AssertOutOfBoundsWrapper                   │
    │       └─> ClipOutOfBoundsWrapper                     │
    │                                                      │
    │                                               aec_to_parallel_wrapper
    │                                               parallel_to_aec_wrapper
    │                                                       │
    └───────────────────────────────────────────────────────┘
```

**关键发现**：`AECEnv` 与 `ParallelEnv` **没有共同父类**（除了 Python 的 `object`），它们是对"多智能体交互"的两种并行抽象。`BaseWrapper` 继承自 `AECEnv`，内部持有 `self.env`，并通过 `__getattr__` 将属性访问代理给被包装环境。

#### 3.1.2 AECEnv 基类深度剖析

源码文件：[`pettingzoo/utils/env.py`](https://github.com/Farama-Foundation/PettingZoo/blob/master/pettingzoo/utils/env.py)

**关键属性**：

```python
class AECEnv(Generic[AgentID, ObsType, ActionType]):
    possible_agents: list[AgentID]      # 所有"可能出现"的智能体（生命周期内上限）
    agents: list[AgentID]               # 当前还活着的智能体
    agent_selection: AgentID            # 当前轮到的智能体

    observation_spaces: dict[AgentID, gymnasium.spaces.Space]
    action_spaces: dict[AgentID, gymnasium.spaces.Space]

    terminations: dict[AgentID, bool]
    truncations: dict[AgentID, bool]
    rewards: dict[AgentID, float]       # 上一步的即时奖励
    _cumulative_rewards: dict[AgentID, float]   # 累计奖励（供 last() 使用）
    infos: dict[AgentID, dict]
```

- `possible_agents` 是**静态上限**，用于环境初始化时确定最大智能体数量、分配空间缓存。
- `agents` 是**动态列表**，智能体死亡后会被移除。环境是否结束通常由 `len(self.agents) == 0` 判断。

**`agent_iter()` 生成器的实现**（[`pettingzoo/utils/env.py`](https://github.com/Farama-Foundation/PettingZoo/blob/master/pettingzoo/utils/env.py)）：

```python
def agent_iter(self, max_iter: int = 2**63) -> AECIterable:
    return AECIterable(self, max_iter)

class AECIterator(Iterator[AgentID]):
    def __next__(self) -> AgentID:
        if not self.env.agents or self.iters_til_term <= 0:
            raise StopIteration
        self.iters_til_term -= 1
        return self.env.agent_selection
```

`agent_iter()` 本身**不推进环境**，它只是一个"读取当前 `agent_selection`"的迭代器。真正的状态推进发生在用户调用 `env.step(action)` 之后，由具体环境的 `step()` 修改 `agent_selection`。

**`last()` 方法：为什么需要它？**

```python
def last(self, observe: bool = True):
    agent = self.agent_selection
    observation = self.observe(agent) if observe else None
    return (
        observation,
        self._cumulative_rewards[agent],
        self.terminations[agent],
        self.truncations[agent],
        self.infos[agent],
    )
```

与 Gymnasium `step()` 的本质区别：

| 维度 | Gymnasium (`Env.step`) | PettingZoo AEC (`Env.step`) |
|---|---|---|
| 返回值 | `obs, reward, terminated, truncated, info` | `None` |
| 动作输入 | 环境的全局动作 | **当前 `agent_selection` 对应的单个智能体的动作** |
| 奖励归属 | 环境返回该步的 reward | `step()` 不返回值，用户通过 `last()` 获取**当前智能体**在上一次 `step()` 中积累的奖励 |

存在原因：
1. AEC 模型是"单步单智能体"：当你调用 `step(action)` 时，你只是在为当前选中的智能体执行动作
2. 奖励是滞后归因的：在 `pistonball` 等环境中，奖励往往在一个 cycle（所有智能体都行动一遍）结束后统一计算。`last()` 返回的是 `_cumulative_rewards`，即自该智能体上次行动以来积累的所有奖励
3. 与 `agent_iter()` 配套使用，代码看起来像"轮流下棋"，非常符合博弈论中的 Extensive Form Game

#### 3.1.3 智能体死亡/新生的处理机制

**死亡处理：`_was_dead_step()`**（[`pettingzoo/utils/env.py`](https://github.com/Farama-Foundation/PettingZoo/blob/master/pettingzoo/utils/env.py)）

```python
def _was_dead_step(self, action: ActionType) -> None:
    if action is not None:
        raise ValueError("when an agent is dead, the only valid action is None")

    agent = self.agent_selection
    del self.terminations[agent]
    del self.truncations[agent]
    del self.rewards[agent]
    del self._cumulative_rewards[agent]
    del self.infos[agent]
    self.agents.remove(agent)

    _deads_order = [a for a in self.agents if self.terminations[a] or self.truncations[a]]
    if _deads_order:
        self.agent_selection = _deads_order[0]
    else:
        if getattr(self, "_skip_agent_selection", None) is not None:
            self.agent_selection = self._skip_agent_selection
        self._skip_agent_selection = None
    self._clear_rewards()
```

- 强制 action 为 `None`：死亡智能体不能执行真实动作，只能被"清场"
- `_skip_agent_selection`：`_deads_step_first()` 会提前把 `agent_selection` 指向第一个死亡智能体，并把原来的 live agent 存到 `_skip_agent_selection`。当所有死 agent 清完后，通过 `_skip_agent_selection` 恢复原有的轮转顺序
- 这保证了 **"死 agent 先走"** 的语义，避免 live agent 在死亡判定前拿到错误的观测

**新生处理**：在 [`parallel_to_aec_wrapper`](https://github.com/Farama-Foundation/PettingZoo/blob/master/pettingzoo/utils/conversions.py) 中可以看到新增智能体的示例——新生智能体被追加到 `agent_order`，并通过 `_agent_selector.next()` 立即激活。

#### 3.1.4 ParallelEnv 基类与 AEC↔Parallel 转换

**`parallel_to_aec_wrapper`**（[`pettingzoo/utils/conversions.py`](https://github.com/Farama-Foundation/PettingZoo/blob/master/pettingzoo/utils/conversions.py)）的核心逻辑：

```python
class parallel_to_aec_wrapper(AECEnv):
    def step(self, action):
        if self.terminations[self.agent_selection] or self.truncations[self.agent_selection]:
            self._was_dead_step(action)
            return

        self._actions[self.agent_selection] = action
        if self._agent_selector.is_last():
            # 所有 live agent 都提交动作后，真正调用 ParallelEnv.step
            obss, rews, terms, truncs, infos = self.env.step(self._actions)
            # ... 复制结果 ...
            if len(self.env.agents):
                self._agent_selector = AgentSelector(self.env.agents)
                self.agent_selection = self._agent_selector.reset()
            self._deads_step_first()
        else:
            if self._agent_selector.is_first():
                self._clear_rewards()
            self.agent_selection = self._agent_selector.next()
```

核心思想：在 AEC 侧维护一个 `_actions` 缓存，每收到一个 live agent 的动作就存下来。只有当 `_agent_selector.is_last()`（即最后一个 live agent 也提交了动作）时，才一次性调用底层 `ParallelEnv.step()`。代价是**延迟**：前面的 agent 必须等后面的 agent 都提交后才能看到真正的环境推进。

#### 3.1.5 AgentSelector：极简轮转调度器

源码文件：[`pettingzoo/utils/agent_selector.py`](https://github.com/Farama-Foundation/PettingZoo/blob/master/pettingzoo/utils/agent_selector.py)

```python
class AgentSelector:
    def next(self) -> Any:
        self._current_agent = (self._current_agent + 1) % len(self.agent_order)
        self.selected_agent = self.agent_order[self._current_agent - 1]
        return self.selected_agent

    def is_last(self) -> bool:
        return self.selected_agent == self.agent_order[-1]
```

循环队列 + `is_last()` 判断。`pistonball` 的 `step()` 正是利用 `is_last()` 来决定是否在一个 cycle 结束后统一计算物理和奖励。

#### 3.1.6 Wrappers 关键实现

**OrderEnforcingWrapper**（[`pettingzoo/utils/wrappers/order_enforcing.py`](https://github.com/Farama-Foundation/PettingZoo/blob/master/pettingzoo/utils/wrappers/order_enforcing.py)）：防止用户在 `reset()` 之前访问状态或调用 `step()`，防御性编程。

**TerminateIllegalWrapper**：利用 `action_mask` 判定动作合法性。一旦检测到非法动作，**直接修改底层 `unwrapped` 环境的终止状态**，绕开正常的 `step()` 流程，保证强一致性。

#### 3.1.7 SuperSuit 源码分析

SuperSuit（[`Farama-Foundation/SuperSuit`](https://github.com/Farama-Foundation/SuperSuit)）是 PettingZoo 的伴随包装器库。

**`shared_wrapper_aec`**（[`supersuit/utils/base_aec_wrapper.py`](https://github.com/Farama-Foundation/SuperSuit/blob/master/supersuit/utils/base_aec_wrapper.py)）的设计亮点：

```python
class shared_wrapper_aec(BaseWrapper):
    def __init__(self, env, modifier_class):
        super().__init__(env)
        self.modifiers = {}
        if hasattr(self.env, "possible_agents"):
            self.add_modifiers(self.env.possible_agents)

    def step(self, action):
        mod = self.modifiers[self.agent_selection]
        action = mod.modify_action(action)
        if self.terminations[self.agent_selection] or self.truncations[self.agent_selection]:
            action = None
        super().step(action)
        self.add_modifiers(self.agents)
        self.modifiers[self.agent_selection].modify_obs(super().observe(self.agent_selection))
```

- 每个智能体拥有独立的 `modifier` 实例（如帧堆叠缓冲区），通过 `possible_agents` 预分配
- `observation_space` 和 `action_space` 用 `lru_cache` 缓存
- `reset()` 和 `step()` 时都会调用 `add_modifiers(self.agents)`，处理动态新增的智能体

**关键包装器**：

| 包装器 | 功能 | 交易场景应用 |
|---|---|---|
| `frame_stack_v1` | 帧堆叠 | 订单簿时间序列观测堆叠 |
| `black_death_v3` | 死亡 agent 零填充 | 离线账户保持占位 |
| `pad_observations_v0` | 异构观测对齐 | 不同策略的观测维度对齐 |
| `pad_action_space_v0` | 异构动作对齐 | 不同策略的动作维度对齐 |
| `clip_actions_v0` | 动作裁剪 | 价格/数量范围约束 |

#### 3.1.8 环境版本控制机制

PettingZoo 采用**严格的外部版本化**：
- 每个环境都有一个版本文件，如 `pistonball_v6.py`，内容极其简单，仅做入口导出
- 核心逻辑放在 `pistonball/pistonball.py`，版本文件仅做导出
- 一旦环境规则、奖励函数、观测空间等发生可能影响训练结果的变更，就增加版本号并新建 `_vN.py`
- 这种设计与 Gymnasium 的 `gym.make("CartPole-v1")` 类似，但 PettingZoo 把它显式化到了文件系统层面

#### 3.1.9 PettingZoo 与 Gymnasium 的关系

- **组织关系**：PettingZoo 与 [Gymnasium](https://github.com/Farama-Foundation/Gymnasium) 同属 [Farama Foundation](https://farama.org/) 维护的开源生态。PettingZoo 明确依赖 `gymnasium>=1.0.0`
- **空间系统**完全复用 `gymnasium.spaces`
- **差异**：Gymnasium 的 `Env.step(action)` 返回五元组；PettingZoo AEC 的 `step()` 返回 `None`，奖励/观测通过 `last()` 获取

#### 3.1.10 对交易环境设计的启示

1. **采用 AEC 语义表达"撮合序贯"**：金融市场的撮合本质上是序贯的（订单按到达时间排序），虽然交易者可以同时提交订单，但撮合引擎内部是顺序执行的。每个 `step(action)` 表示提交一笔订单，`is_last()` 时触发撮合引擎统一计算市场状态变化和奖励
2. **`last()` + `_cumulative_rewards` 的奖励归因模式**：交易奖励往往不能在单次动作后立即确定（如持仓盈亏需要等到平仓或周期结束）。`_cumulative_rewards` 的设计允许延迟归因
3. **`possible_agents` 与动态 `agents` 管理账户生命周期**：`possible_agents` 设为所有可能被激活的策略账户（固定上限），`agents` 动态增减模拟"开户/销户"
4. **版本化环境**：交易规则（手续费、滑点、涨跌停）极度敏感，每次修改规则时新建版本文件，保证回测结果可复现
5. **动作掩码 (`action_mask`)**：交易中存在大量非法动作（超出涨跌停价的挂单、超出可用资金的买入、没有持仓时的卖出），可在 `obs` 或 `info` 中返回 `action_mask`

---

### 3.2 MARLlib + RLlib

**项目信息**
| 属性 | 内容 |
|------|------|
| 组织 | 独立开源项目 / [Anyscale](https://www.anyscale.com/) |
| 定位 | MARL 训练框架（MARLlib 高级封装 / RLlib 底层基础设施） |
| 后端 | [Ray](https://github.com/ray-project/ray) / RLlib |
| 核心论文 | [*MARLlib: A Scalable and Efficient Library For Multi-agent Reinforcement Learning*](https://arxiv.org/abs/2210.13708) (2022) |
| 官方文档 | [marllib.readthedocs.io](https://marllib.readthedocs.io/) / [docs.ray.io/rllib](https://docs.ray.io/en/latest/rllib/index.html) |
| GitHub | [Replicable-MARL/MARLlib](https://github.com/Replicable-MARL/MARLlib) / [ray-project/ray](https://github.com/ray-project/ray) |

#### 3.2.1 核心问题：RLlib 的多智能体缺陷

MARLlib 明确指出 [Ray RLlib](https://docs.ray.io/en/latest/rllib/index.html) 的多智能体支持存在三大问题：

1. **缺乏标准化的智能体-环境接口**：RLlib 的多智能体接口过于灵活，没有统一约定
2. **新手不友好**：需要深入理解 RLlib 内部机制才能使用多智能体功能
3. **算法集成缺乏统一框架**：不同算法之间难以比较和组合

#### 3.2.2 MARLlib 的核心设计：统一接口层

MARLlib 在 RLlib 之上增加了一层**统一的多智能体抽象**：

| 特性 | RLlib | MARLlib |
|------|-------|---------|
| 任务接口与转移数据 | 模糊 & 灵活 | 结构化 |
| 多智能体算法支持 | 简单扩展 | 标准 CTDE（Centralized Training Decentralized Execution） |
| 策略映射与参数共享 | 手动配置 | 自动适配 |
| 新手友好度 | 难 | 易 |
| 自动适配与兼容性测试 | ❌ | ✅ |
| 实验与基准测试 | 有限 | 全面 |

**关键创新：数据流等价性**

MARLlib 证明了所有多智能体学习范式都可以转化为等价的"聚合单智能体学习过程"：
- **独立学习**：每个智能体维护自己的数据缓冲区（而非集中式缓冲）
- **中心化评论者**：全局状态通过信息共享机制注入
- **值分解**（VDN/QMIX）：在训练阶段分解联合值函数

#### 3.2.3 Centralized Critic 的 Postprocessing 注入模式

源码文件：[`marllib/marl/algos/utils/centralized_critic.py`](https://github.com/Replicable-MARL/MARLlib/blob/main/marllib/marl/algos/utils/centralized_critic.py)

这是 MARLlib 最重要的技术贡献之一。传统 RLlib 原生不支持 centralized critic，需要用户自定义 Policy。MARLlib 采用 **Postprocessing 注入模式**：

```python
def centralized_critic_postprocessing(policy, sample_batch, other_agent_batches=None):
    # 1. 从 other_agent_batches 提取对手 obs/action
    # 2. 构造全局 state（拼接所有智能体观测 + 全局信息）
    # 3. 用 central_value_function 计算全局价值
    # 4. 将计算结果注入 sample_batch["state_value"]
```

优势：**无需修改 RLlib 采样管线**，在 postprocessing 阶段注入全局信息即可。

#### 3.2.4 RLlib 的多智能体核心机制

**MultiAgentEnv 基类**（[`ray/rllib/env/multi_agent_env.py`](https://github.com/ray-project/ray/blob/master/rllib/env/multi_agent_env.py)）：

```python
class MultiAgentEnv:
    def reset(self, *, seed=None, options=None):
        # 返回 {agent_id: observation}
        return {"agent_1": obs1, "agent_2": obs2}

    def step(self, action_dict):
        # action_dict: {agent_id: action}
        return (
            {"agent_1": obs1, "agent_2": obs2},   # observations
            {"agent_1": r1, "agent_2": r2},       # rewards
            {"agent_1": False, "agent_2": True},   # terminated
            {"agent_1": False, "agent_2": False},  # truncated
            {"agent_1": {}, "agent_2": {}}         # infos
        )
```

**PolicyMap**（[`ray/rllib/policy/policy_map.py`](https://github.com/ray-project/ray/blob/master/rllib/policy/policy_map.py)）：LRU 缓存 + `policy_states_are_swappable`，用于在内存受限时换出不活跃的策略。

**MultiAgentBatch**（[`ray/rllib/policy/sample_batch.py`](https://github.com/ray-project/ray/blob/master/rllib/policy/sample_batch.py)）：

```python
class MultiAgentBatch:
    # Dict[PolicyID, SampleBatch]
    # 每个 PolicyID 独立 batch，支持 timeslices() 做 lockstep 切分
```

**Replay Buffer**（[`ray/rllib/utils/replay_buffers/multi_agent_replay_buffer.py`](https://github.com/ray-project/ray/blob/master/rllib/utils/replay_buffers/multi_agent_replay_buffer.py)）：每个 PolicyID 独立 buffer，支持 `independent` / `lockstep` 两种模式。

#### 3.2.5 参数共享策略

MARLlib 支持三种参数共享模式：
- `share`：所有智能体共享同一策略网络
- `group`：按智能体分组共享
- `separate`：每个智能体独立网络

这是自动配置的，根据环境特征和算法要求自动选择最优策略。

#### 3.2.6 对交易环境设计的启示

1. **环境接口**：采用 `MultiAgentEnv` + `Dict{"obs", "state", "action_mask"}` 观测空间
2. **主算法推荐**：**MAPPO + Centralized Critic**，通过全局市场状态和其他 agent 订单/持仓提升 Critic 精度
3. **参数共享**：同质交易 agent 用 `share_policy="all"`，异构策略用 `group` 或 `individual`
4. **缓冲区**：交易数据具有 episode 结构（交易日），优先考虑 episode-based buffer；市场非平稳性强，建议以 **on-policy 算法为主**
5. **Centralized Critic 实现**：直接复用 MARLlib 的 Postprocessing 注入模式

---

### 3.3 Melting Pot

**项目信息**
| 属性 | 内容 |
|------|------|
| 组织 | [DeepMind](https://deepmind.google/) / Google |
| 定位 | 社会困境（Social Dilemma）多智能体评估套件 |
| 核心论文 | [*Melting Pot: multi-agent reinforcement learning for artificial societies*](https://arxiv.org/abs/2107.06875) (2021) |
| 官方文档 | [github.com/google-deepmind/meltingpot](https://github.com/google-deepmind/meltingpot) |
| GitHub | [google-deepmind/meltingpot](https://github.com/google-deepmind/meltingpot) |
| 底层引擎 | DM Lab2D（基于 Lua 的 2D 网格世界引擎） |
| 规模 | 50+ substrates，256+ scenarios |

#### 3.3.1 核心理念：评估社会智能

Melting Pot 与其他 MARL 框架的根本区别在于：它**不是通用环境库，而是专门设计来评估智能体的社会行为**。重点关注：合作与竞争、信任与欺骗、互惠与惩罚、规范形成、零样本泛化。

#### 3.3.2 架构：Substrate + Scenario

```
Melting Pot
├── Substrate（基质/基础环境）
│   └── 定义物理规则、动作空间、观测空间
│   └── 例如：Commons Harvest: Open
├── Scenario（场景/任务变体）
│   └── 在 Substrate 上配置智能体角色、奖励函数、初始状态
│   └── 例如：A 组智能体自私，B 组智能体合作
```

**Substrate 构建管线**（[`meltingpot/utils/substrates/substrate.py`](https://github.com/google-deepmind/meltingpot/blob/main/meltingpot/utils/substrates/substrate.py)）：

```python
def build_substrate(*, lab2d_settings, individual_observations,
                    global_observations, action_table) -> Substrate:
    env = builder.builder(lab2d_settings)          # 1. 构建底层 DM Lab2D 环境
    env = observables_wrapper.ObservablesWrapper(env)  # 2. ReactiveX observable 流
    env = multiplayer_wrapper.Wrapper(env, ...)    # 3. 转换为多人列表格式
    env = discrete_action_wrapper.Wrapper(env, action_table)  # 4. 离散动作映射
    env = collective_reward_wrapper.CollectiveRewardWrapper(env)  # 5. 集体奖励
    return Substrate(env)
```

关键 Wrapper 的作用：
- `ObservablesWrapper`：将 DM Lab2D 包装为 ReactiveX observable 流，暴露 `action`、`timestep`、`events` 三个流
- `MultiplayerWrapper`：将扁平化观测/动作转换为按玩家索引的列表格式
- `CollectiveRewardWrapper`：在每个玩家的观测中注入 `COLLECTIVE_REWARD`（所有玩家奖励之和），为社会困境研究提供关键信号

#### 3.3.3 DM Lab2D 的集成方式（Lua 层与 Python 层的交互）

Python → Lua 的配置传递（[`meltingpot/utils/substrates/builder.py`](https://github.com/google-deepmind/meltingpot/blob/main/meltingpot/utils/substrates/builder.py)）：

```python
def parse_python_settings_for_dmlab2d(lab2d_settings):
    lab2d_settings = settings_helper.flatten_args(lab2d_settings)
    for key, value in lab2d_settings.items():
        converted_key = key.replace("$", ".")  # 用 "$" 代替 "." 以兼容 ConfigDict
        lab2d_settings_dict[converted_key] = str(value)
    return lab2d_settings_dict
```

Lua 层的核心架构（[`meltingpot/lua/modules/api_factory.lua`](https://github.com/google-deepmind/meltingpot/blob/main/meltingpot/lua/modules/api_factory.lua)）：

```lua
local function apiFactory(env)
  local api = {
      _observations = {{name = 'GLOBAL.TEXT', type = 'String', ...}},
      _settings = {env_seed = 1, numPlayers = 1, ...}
  }
  function api:advance(steps)
    self.simulation:update(self._grid)
    self._grid:update(random)
    return continue, self.simulation:getReward()
  end
end
```

Python 通过 `dmlab2d.Lab2d(_DMLAB2D_ROOT, lab2d_settings_dict)` 启动 Lua 运行时。

#### 3.3.4 Scenario 的配置方式（社会结构的叠加）

[`meltingpot/utils/scenarios/scenario.py`](https://github.com/google-deepmind/meltingpot/blob/main/meltingpot/utils/scenarios/scenario.py)：

```python
class Scenario(substrate_lib.Substrate):
    def __init__(self, substrate, background_population, is_focal,
                 permitted_observations):
        self._substrate = substrate
        self._background_population = background_population  # Bot 种群
        self._is_focal = is_focal          # 哪些槽位是 focal 玩家
        self._permitted_observations = permitted_observations  # 观测过滤
```

关键机制：
1. **动作合并**（`_await_full_action`）：focal 玩家提交动作后，Scenario 异步等待 background bots 的动作，合并为完整动作向量
2. **观测分割与过滤**（`_split_timestep`）：Substrate 返回的多人观测被分割为 focal 观测和 background 观测；focal 观测按 `permitted_observations` 过滤
3. **角色系统**：支持异构角色（如 "defender", "harvester"），不同角色可填充不同的 bot 策略

#### 3.3.5 Bot 系统（背景智能体的实现）

[`meltingpot/utils/policies/policy.py`](https://github.com/google-deepmind/meltingpot/blob/main/meltingpot/utils/policies/policy.py)：

```python
class Policy(Generic[State], metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def step(self, timestep: dm_env.TimeStep, prev_state: State) -> Tuple[int, State]: ...
```

[`meltingpot/utils/policies/population.py`](https://github.com/google-deepmind/meltingpot/blob/main/meltingpot/utils/policies/population.py) 使用 `ThreadPoolExecutor` 实现 bots 的并行推理：

```python
class Population:
    def send_timestep(self, timestep: dm_env.TimeStep) -> None:
        for n, step_fn in enumerate(self._step_fns):
            bot_timestep = timestep._replace(
                observation=timestep.observation[n], reward=timestep.reward[n])
            future = self._executor.submit(step_fn, bot_timestep)
            self._action_futures.append(future)

    def await_action(self) -> Sequence[int]:
        actions = tuple(future.result() for future in self._action_futures)
        return actions
```

#### 3.3.6 评估协议：Focal Per Capita Return

[`meltingpot/utils/evaluation/return_subject.py`](https://github.com/google-deepmind/meltingpot/blob/main/meltingpot/utils/evaluation/return_subject.py)：

```python
class ReturnSubject(subject.Subject):
    def on_next(self, timestep: dm_env.TimeStep) -> None:
        if timestep.step_type.first():
            self._return = np.zeros_like(timestep.reward)
        self._return += timestep.reward
        if timestep.step_type.last():
            super().on_next(self._return)
```

核心评估指标：
- `focal_player_returns`：每个 focal 玩家的 episode 总回报
- `focal_per_capita_return`：focal 玩家的平均回报
- **零样本泛化**：训练好的智能体放入全新社会组合中（与未训练过的智能体交互），评估适应能力

#### 3.3.7 SocialJAX：JAX 重实现

SocialJAX 是 Melting Pot 的 [JAX 重实现](https://github.com/DarylRodrigo/SocialJAX)，核心改进：
- 将 Melting Pot 的 6 个核心社会环境用 JAX 重写，支持 GPU/TPU 并行
- 从像素级 RGB（88×88×3）降级为网格级数值观测
- 在 A100 GPU 上，SocialJAX 的随机动作步进速度是 Melting Pot 2.0 的 **40-400 倍**；完整 IPPO 训练管线快 **50 倍以上**

#### 3.3.8 对交易环境设计的启示

| Melting Pot 概念 | 交易市场对应 |
|-----------------|-------------|
| Substrate | 市场微结构（订单簿规则、撮合机制、结算规则） |
| Scenario | 特定的市场参与者结构（散户、做市商、套利者、操纵者） |
| Focal Agent | 待评估的交易策略 |
| Background Bots | 基准市场参与者策略（如恒定做市商、趋势跟随者） |
| Focal Per Capita Return | 策略在多样化对手种群中的平均夏普比率 / PnL |
| Collective Reward | 市场整体福利（如价差缩小、流动性提升） |

- 交易本质上是社会困境：每个交易者的个体最优（套利）可能导致集体次优（市场崩盘）
- 采用 **Substrate/Scenario 双层架构**：底层定义撮合引擎和资产动态，上层配置参与者角色
- 引入 **CollectiveRewardWrapper**：在观测中注入市场整体指标，促使策略学习社会最优行为
- 使用 **Puppeteer/Bot 系统**实现自适应的背景交易者
- 评估时采用 **Focal Per Capita Return**：在多种背景种群组合上测试策略的泛化能力

---

### 3.4 OpenSpiel

**项目信息**
| 属性 | 内容 |
|------|------|
| 组织 | [DeepMind](https://deepmind.google/) / Google |
| 定位 | 博弈论 + RL 的通用框架 |
| 核心论文 | [*OpenSpiel: A Framework for Reinforcement Learning in Games*](https://arxiv.org/abs/1908.09453) (2019) |
| 官方文档 | [openspiel.readthedocs.io](https://openspiel.readthedocs.io/) |
| GitHub | [google-deepmind/open_spiel](https://github.com/google-deepmind/open_spiel) |
| 实现语言 | C++ 核心 + Python 绑定 |
| 规模 | 50+ 种游戏，20+ 种算法 |

#### 3.4.1 EFG 核心类图

OpenSpiel 的核心对象模型围绕**扩展式博弈树（Extensive-Form Game Tree）**构建：

```
┌─────────────────────────────────────────────────────────────┐
│                         pyspiel.Game                         │
│  ├─ get_type() → GameType (dynamics, chance_mode, info, ...)│
│  ├─ num_players()                                           │
│  ├─ num_distinct_actions()                                  │
│  ├─ new_initial_state() → State                             │
│  └─ observation_tensor_size() / information_state_tensor_size()│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                         pyspiel.State                        │
│  ├─ current_player() → 0,1,... | kChancePlayerId(-1) |     │
│  │                    kSimultaneousPlayerId(-2)              │
│  ├─ is_terminal() / is_chance_node() / is_simultaneous_node()│
│  ├─ legal_actions() / legal_actions(player)                 │
│  ├─ apply_action(action) / apply_actions([a0, a1, ...])     │
│  ├─ returns() / rewards()                                   │
│  ├─ information_state_string(player)                        │
│  ├─ information_state_tensor(player)                        │
│  ├─ observation_string(player)                              │
│  ├─ observation_tensor(player)                              │
│  ├─ chance_outcomes() → [(action, prob), ...]               │
│  └─ clone() / history() / move_number()                     │
└─────────────────────────────────────────────────────────────┘
```

**关键设计决策**：
- `State` 是**值语义**的（可通过 `clone()` 复制），支持博弈树搜索中的状态回溯
- `Game` 是**不可变工厂**，通过 `GameParameters` 实例化后创建初始状态

#### 3.4.2 Information State vs Observation

在 [`open_spiel/spiel.h`](https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/spiel.h) 中有精确定义：

**Information State（信息集）**：
> "The information state is a perfect-recall state-of-the-game from the perspective of one player."

在 Kuhn Poker（不完美信息）中，`InformationStateString` 只包含玩家可见的信息（自己的牌 + 公开的 betting history），不包含对手的牌。

**Observation**：
> "An observation is some subset of the information state with the property that remembering all the player's observations and actions is sufficient to reconstruct the information state."

在 [`open_spiel/python/rl_environment.py`](https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/python/rl_environment.py) 中，两者的切换通过 `observation_type` 参数控制：

```python
class ObservationType(enum.Enum):
    OBSERVATION = 0          # 使用 observation_tensor
    INFORMATION_STATE = 1    # 使用 information_state_tensor
```

#### 3.4.3 Chance Node 与 Simultaneous Move

Chance Node 在代码中通过 `kChancePlayerId = -1` 标识：

```cpp
virtual bool IsChanceNode() const {
    return CurrentPlayer() == kChancePlayerId;
}
```

在 [`rl_environment.py`](https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/python/rl_environment.py) 中，Chance Node 对 Agent 完全透明：

```python
def _sample_external_events(self):
    while self._state.is_chance_node():
        outcome = self._chance_event_sampler(self._state)
        self._state.apply_action(outcome)
```

同时移动游戏通过 `kSimultaneousPlayerId = -2` 标识：

```python
@property
def is_turn_based(self):
    return self._game.get_type().dynamics == pyspiel.GameType.Dynamics.SEQUENTIAL

def step(self, actions):
    if self.is_turn_based:
        self._state.apply_action(actions[0])      # 轮流：1 个动作
    else:
        self._state.apply_actions(actions)         # 同时：N 个动作
```

#### 3.4.4 TabularPolicy 与 CFR 算法

**TabularPolicy**（[`open_spiel/python/policy.py`](https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/python/policy.py)）：

```python
class TabularPolicy(Policy):
    def __init__(self, game, players=None, ...):
        states = get_all_states.get_all_states(game, include_chance_states=False, ...)
        for player in players:
            for _, state in sorted(states.items()):
                if state.is_simultaneous_node() or player == state.current_player():
                    key = self._state_key(state, player)
                    self.state_lookup[key] = state_index
                    legal_actions_list.append(state.legal_actions_mask(player))
        self.legal_actions_mask = np.array(legal_actions_list)
        self.action_probability_array = (
            self.legal_actions_mask / np.sum(self.legal_actions_mask, axis=-1, keepdims=True))
```

以 `(num_states, num_actions)` 的数组存储策略，使用 `state.information_state_string()` 作为状态键。

**外部采样 MCCFR**（[`open_spiel/python/algorithms/external_sampling_mccfr.py`](https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/python/algorithms/external_sampling_mccfr.py)）：

```python
def _update_regrets(self, state, player):
    if state.is_terminal(): return state.player_return(player)
    if state.is_chance_node():
        outcome = np.random.choice(*zip(*state.chance_outcomes()))
        return self._update_regrets(state.child(outcome), player)

    cur_player = state.current_player()
    policy = self._regret_matching(...)

    if cur_player != player:
        # 对手节点：采样一个动作（外部采样）
        action_idx = np.random.choice(np.arange(num_legal_actions), p=policy)
        return self._update_regrets(state.child(legal_actions[action_idx]), player)
    else:
        # 当前玩家节点：遍历所有动作计算反事实后悔值
        for action_idx in range(num_legal_actions):
            child_values[action_idx] = self._update_regrets(state.child(...), player)
        for action_idx in range(num_legal_actions):
            self._add_regret(info_state_key, action_idx, child_values[action_idx] - value)
```

核心思想：在对手节点和 Chance 节点上**采样**动作（而非遍历），只在当前更新玩家的节点上遍历所有动作计算后悔值，大幅降低每次迭代的计算复杂度。

#### 3.4.5 对交易环境设计的启示

| 交易环境概念 | OpenSpiel 对应 |
|-------------|----------------|
| 公开市场数据（价格、成交量） | `ObservationString` / `ObservationTensor` |
| 私有信息（持仓、成本线、策略信号） | `InformationStateString`（含完美回忆的历史） |
| 市场随机冲击（宏观新闻、流动性冲击） | `ChanceNode` with `chance_outcomes()` |
| 同时下单 | `SimultaneousNode` (`kSimultaneousPlayerId`) |

- 将订单簿状态编码为 `ObservationTensor`（公共观测）
- 将代理的完整交易历史编码为 `InformationStateTensor`（用于训练基于信息集的算法如 CFR、MCCFR）
- 用 `ChanceNode` 模拟外部市场冲击（如随机到来的大订单）
- CFR 类算法可以用于计算近似纳什均衡策略

---

### 3.5 BenchMARL

**项目信息**
| 属性 | 内容 |
|------|------|
| 组织 | [Meta](https://ai.meta.com/) / Facebook Research |
| 定位 | MARL **标准化基准测试**训练库 |
| 后端 | [TorchRL](https://github.com/pytorch/rl) |
| 核心论文 | [*BenchMARL: Benchmarking Multi-Agent Reinforcement Learning*](https://arxiv.org/abs/2312.01472) (2023) |
| 官方文档 | [facebookresearch.github.io/BenchMARL](https://facebookresearch.github.io/BenchMARL/) |
| GitHub | [facebookresearch/BenchMARL](https://github.com/facebookresearch/BenchMARL) |

#### 3.5.1 核心问题：MARL 的可复现性危机

BenchMARL 指出 MARL 领域面临严重的可复现性问题：不同论文的实现细节差异巨大（超参数、网络结构、数据预处理），缺乏标准化的基准测试流程。

#### 3.5.2 设计：系统化配置 + 报告

BenchMARL 基于 [Hydra](https://hydra.cc/) 配置系统：

```yaml
# benchmarl/conf/experiment/base_experiment.yaml
defaults:
  - experiment_config
  - _self_

sampling_device: "cpu"
train_device: "cpu"
share_policy_params: True
gamma: 0.99
lr: 0.00005
on_policy_collected_frames_per_batch: 6000
on_policy_n_envs_per_worker: 10
evaluation_interval: 120_000
loggers: [csv, wandb]
```

```bash
# 一键运行跨算法、跨模型、跨任务的完整基准测试
python run.py algorithm=ippo,mappo,qmix task=vmas/navigation,vmas/balance
```

#### 3.5.3 核心架构

```
BenchMARL
├── Benchmark（基准测试集合）
│   └── 一组共享超参数的实验
├── Algorithm（算法）
│   └── IPPO, MAPPO, MADDPG, MASAC, ISAC, QMIX, VDN, IQL...
├── Model（模型架构）
│   └── MLP, LSTM, GNN (HetGPPO)
└── Task（任务/环境）
    └── VMAS, SMAC, MPE, GRF, MAMuJoCo, MAgent
```

#### 3.5.4 算法实现：MAPPO

[`benchmarl/algorithms/mappo.py`](https://github.com/facebookresearch/BenchMARL/blob/main/benchmarl/algorithms/mappo.py)：

```python
def _get_loss(self, group, policy_for_loss, continuous):
    loss_module = ClipPPOLoss(
        actor=policy_for_loss,
        critic=self.get_critic(group),
        clip_epsilon=self.clip_epsilon,
        entropy_coeff=self.entropy_coef,
        critic_coeff=self.critic_coef,
        loss_critic_type=self.loss_critic_type,
        normalize_advantage=False,
    )
    loss_module.set_keys(
        reward=(group, "reward"),
        action=(group, "action"),
        done=(group, "done"),
        advantage=(group, "advantage"),
        value_target=(group, "value_target"),
        value=(group, "state_value"),
    )
    loss_module.make_value_estimator(
        ValueEstimators.GAE, gamma=self.experiment_config.gamma, lmbda=self.lmbda
    )
    return loss_module, False
```

- **Centralized Critic**：通过 `get_critic()` 构建，可选 `share_param_critic`，支持全局状态输入或观测拼接
- **minibatch_advantage**：当 `minibatch_advantage=True` 时，GAE 计算在 minibatch 上进行，避免全 batch 内存爆炸
- **动作分布**：连续动作用 `TanhNormal`，离散动作用 `MaskedCategorical`（支持动作掩码）

#### 3.5.5 GNN 模型：HetGPPO

[`benchmarl/models/gnn.py`](https://github.com/facebookresearch/BenchMARL/blob/main/benchmarl/models/gnn.py)：

```python
def _forward(self, tensordict):
    graph = _batch_from_dense_to_ptg(
        x=input, edge_index=self.edge_index, pos=pos, vel=vel
    )
    forward_gnn_params = {
        "x": graph.x,
        "edge_index": graph.edge_index,
        "edge_attr": graph.edge_attr,
    }
    res = self.gnns[0](**forward_gnn_params).view(
        *batch_size, self.n_agents, self.output_features
    )
```

- 支持 `full`, `empty`, `from_pos` 三种拓扑
- 动态图构建（`from_pos` 使用 `radius_graph`）
- 与 PyTorch Geometric 深度集成

#### 3.5.6 实验结果记录与报告机制

`Logger` 类聚合了多后端日志（Wandb、TensorBoard、CSV、JSON）：

```json
{
  "environment_name": {
    "task_name": {
      "algorithm_name": {
        "seed_0": {
          "step_0": {"step_count": 0, "return": [...]},
          "absolute_metrics": {"return": [max_value]}
        }
      }
    }
  }
}
```

#### 3.5.7 对交易环境设计的启示

BenchMARL 强调**标准化和可复现性**：
- 不同交易策略的比较必须基于完全相同的回测条件
- 需要记录完整的实验配置（市场参数、智能体初始资金、观测窗口等）
- 建议采用 Hydra 或类似配置管理系统
- 分层日志：per-agent → per-group → global
- 检查点机制：支持中断恢复（对长周期回测至关重要）

---

### 3.6 VMAS

**项目信息**
| 属性 | 内容 |
|------|------|
| 组织 | [proroklab](https://github.com/proroklab) / University of Cambridge |
| 定位 | 向量化多智能体物理仿真器 |
| 后端 | 纯 [PyTorch](https://pytorch.org/) |
| GitHub | [proroklab/VectorizedMultiAgentSimulator](https://github.com/proroklab/VectorizedMultiAgentSimulator) |
| 维护状态 | 活跃，BenchMARL 主要后端之一 |

#### 3.6.1 核心架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Environment                             │
│  ┌─────────────┐    ┌─────────────────────────────────────┐ │
│  │   Scenario  │───▶│           World (core.py)           │ │
│  │  (task def) │    │  ┌─────┐ ┌─────┐      ┌──────────┐ │ │
│  └─────────────┘    │  │Agent│ │Agent│ ...  │ Landmark │ │ │
│                     │  └─────┘ └─────┘      └──────────┘ │ │
│  ┌─────────────┐    │     │        │                      │ │
│  │  make_env   │    │  AgentState (pos, vel, rot, force)  │ │
│  │  (batch_dim)│    │     └──►  TorchVectorizedObject    │ │
│  └─────────────┘    └─────────────────────────────────────┘ │
│                              │                              │
│                              ▼                              │
│              Vectorized Step (single PyTorch graph)         │
└─────────────────────────────────────────────────────────────┘
```

#### 3.6.2 向量化执行机制

[`vmas/simulator/environment.py`](https://github.com/proroklab/VectorizedMultiAgentSimulator/blob/main/vmas/simulator/environment.py)：

```python
class Environment(TorchVectorizedObject):
    def __init__(self, scenario, num_envs=32, device="cpu", ...):
        self.num_envs = num_envs
        self.world = self.scenario.env_make_world(self.num_envs, self.device)

    def step(self, actions):
        # actions: List[Tensor], 每个 Tensor 形状为 (num_envs, action_size)
        for i, agent in enumerate(self.agents):
            self._set_action(actions[i], agent)

        self.scenario.pre_step()
        self.world.step()      # 物理仿真（向量化）
        self.scenario.post_step()
        self.steps += 1

        return self._get_from_scene(
            get_observations=True, get_rewards=True, get_dones=True, get_infos=True,
        )
```

**关键向量化特性**：
- 所有实体状态（`pos`, `vel`, `rot`）都是 shape `(batch_dim, ...)` 的 Tensor
- 物理计算（碰撞检测、距离计算）全部是 batched PyTorch 操作
- `reset_at(index)` 支持单独重置某个环境，而不影响其他并行环境

#### 3.6.3 GPU 加速

VMAS 原生支持 GPU：

```python
env = make_env("navigation", num_envs=256, device="cuda")
obs = env.reset()  # 所有张量在 CUDA 上
obs, rews, dones, info = env.step(actions)  # 全程 GPU
```

#### 3.6.4 与 PettingZoo API 的关系

VMAS **不直接兼容 PettingZoo API**。它提供自己的 API，但通过 Wrapper 适配其他框架：

```python
def make_env(..., wrapper=None, ...):
    # wrapper 可选: "gym", "gymnasium", "rllib", "gymnasium_vec"
    return wrapper.get_env(env) if wrapper is not None else env
```

#### 3.6.5 对交易环境设计的启示

- **向量化回测架构**：交易数据天然是时间序列，可通过 batch 维度并行多个回测窗口
- **GPU 全程加速**：所有计算可用 PyTorch 在 GPU 上完成，向量化回测可达微秒级延迟
- **单独重置**：`reset_at(index)` 支持单独重置某个回测窗口，适合在线学习场景

---

### 3.7 SMACv2

**项目信息**
| 属性 | 内容 |
|------|------|
| 组织 | [oxwhirl](https://github.com/oxwhirl) |
| 定位 | 离散动作 Meta-MARL 基准 |
| GitHub | [oxwhirl/smacv2](https://github.com/oxwhirl/smacv2) |
| 底层引擎 | StarCraft II + [PySC2](https://github.com/deepmind/pysc2) |
| 核心改进 | 部分可观测、异构智能体、随机能力 |

#### 3.7.1 与 SMACv1 的核心改进

| 特性 | SMACv1 | SMACv2 |
|------|--------|--------|
| 观测 | 完全可观测（sight range 内） | 支持**部分可观测**（conic FOV） |
| 智能体 | 同构（固定单位类型） | **异构**（随机单位类型组合） |
| 敌人观测 | 完全可见 | **概率性敌人观测**（`prob_obs_enemy`） |
| 起始位置 | 固定 | **随机起始位置分布** |

#### 3.7.2 观测遮蔽（Observation Masking）

**锥形视野（Conic FOV）**：

```python
def is_position_in_cone(self, agent_id, pos, range="sight_range"):
    distance = self.distance(ally_pos.x, ally_pos.y, pos.x, pos.y)
    if distance > unit_range:
        return False
    obj_angle = np.arctan((pos.y - ally_pos.y) / x_diff)
    fov_angle = np.arctan(self.fov_directions[agent_id][1] / x_diff)
    return np.abs(obj_angle - fov_angle) < self.conic_fov_angle / 2
```

**敌人观测概率（`prob_obs_enemy`）**：

```python
if self.enemy_tags[e_id] is None:
    self.obs_enemies[e_id, agent_id] = 1
    self.enemy_tags[e_id] = agent_id
    for a_id in range(self.n_agents):
        if a_id != agent_id:
            draw = np.random.rand()
            if draw < self.prob_obs_enemy:
                self.obs_enemies[e_id, a_id] = 1
if self.obs_enemies[e_id, agent_id] == 0:
    enemy_visible = False
```

#### 3.7.3 动作掩码（Action Masking）

```python
def get_avail_agent_actions(self, agent_id):
    avail_actions = [0] * self.n_actions
    # 死亡 agent 只能 no-op
    # 移动动作根据 pathing_grid 判断是否可用
    # 攻击动作根据 shoot_range 判断是否可用
```

#### 3.7.4 对交易环境设计的启示

| SMACv2 特性 | 交易环境对应 |
|-------------|-------------|
| `conic_fov` | **市场局部观测**（只观测相关板块/资产） |
| `prob_obs_enemy` | **信息延迟/噪声**（模拟非完美市场数据） |
| `enemy_mask` | **资产遮蔽**（某些资产在特定时期不可交易） |
| `action_mask` | **涨跌停掩码**、**停牌掩码** |

---

### 3.8 JAXMARL

**项目信息**
| 属性 | 内容 |
|------|------|
| 组织 | [FLAIROx](https://github.com/FLAIROx) / University of Oxford |
| 定位 | 基于 [JAX](https://github.com/google/jax) 的高性能 MARL |
| GitHub | [FLAIROx/JaxMARL](https://github.com/FLAIROx/JaxMARL) |
| 后端 | JAX + [Flax](https://github.com/google/flax) |

#### 3.8.1 环境基类：JIT 编译

[`jaxmarl/environments/multi_agent_env.py`](https://github.com/FLAIROx/JaxMARL/blob/main/jaxmarl/environments/multi_agent_env.py)：

```python
class MultiAgentEnv:
    @partial(jax.jit, static_argnums=(0,))
    def step(self, key, state, action):
        # auto-reset 通过 jax.lax.select 切换状态
        obs, state, reward, done, info = self._step(key, state, action)
        obs_re, state_re = self.reset(key)
        state = jax.tree_map(lambda x, y: jax.lax.select(done, x, y), state_re, state)
        return obs, state, reward, done, info
```

- `@partial(jax.jit, static_argnums=(0,))` 实现静态 JIT 编译（self 是静态的，其他参数是 traced）
- `step()` 内置 auto-reset：通过 `jax.lax.select` 在 episode 结束时自动切换为 reset 状态
- 所有交互以 `Dict[str, Array]` 字典化传递

#### 3.8.2 SMAX：纯 JAX 重写的 StarCraft

[`jaxmarl/environments/smax/smax_env.py`](https://github.com/FLAIROx/JaxMARL/blob/main/jaxmarl/environments/smax/smax_env.py)：

- 纯 JAX 重写，无需 StarCraft II 引擎
- 状态用 `flax.struct.dataclass` 管理
- 支持经典地图和 SMACv2 随机变体

#### 3.8.3 训练循环：端到端 JIT

[`jaxmarl/training/ippo_rnn.py`](https://github.com/FLAIROx/JaxMARL/blob/main/jaxmarl/training/ippo_rnn.py)：

- 基于 PureJaxRL 的单文件实现
- `jax.vmap` 并行多环境
- `jax.lax.scan` 收集轨迹
- `nn.scan` 处理 RNN
- **整个 `train` 函数可端到端 JIT**

#### 3.8.4 性能基准

A100 实测：
- **10000 环境并行**：Overcooked 达 **8500x 加速**、MPE 达 **480x 加速**
- 算法训练：SMAX 上单轮 IPPO PyTorch 需 44 小时，JAXMARL 仅需 3.3 分钟（**~40,000x 加速**）
- QMIX 1024 轮并行仅需 198 秒（**21,500x/轮**）

#### 3.8.5 对交易环境设计的启示

- 如需**大规模多智能体回测**，参考 JAXMARL 用 JAX 重写核心仿真，可获得 **1000x-10000x** 吞吐提升
- `Dict[str, Array]` Parallel API 天然支持异构交易智能体（做市商、套利者、趋势跟踪者）

---

### 3.9 补充框架概览

| 框架 | GitHub | 核心特点 | 交易关联 |
|------|--------|----------|----------|
| **MAgent2** | [Farama-Foundation/MAgent2](https://github.com/Farama-Foundation/MAgent2) | C++ 后端通过 `ctypes` 调用，事件驱动奖励 AST，支持 **162+ 智能体**同时运行 | ⭐⭐⭐ |
| **Neural MMO** | [NeuralMMO/client](https://github.com/NeuralMMO/client) | 持久化开放世界，**经济系统**（环境级市场、职业专业化、物品交易）最接近真实金融市场 | ⭐⭐⭐⭐ |
| **Overcooked-AI** | [HumanCompatibleAI/overcooked_ai](https://github.com/HumanCompatibleAI/overcooked_ai) | 两智能体协作烹饪，Human-AI 协调最常用基准 | ⭐⭐ |
| **GRF** | [google-research/football](https://github.com/google-research/football) | 物理 3D 足球，19 动作，支持 11v11 | ⭐⭐ |
| **RWARE** | [uoe-agents/robotic-warehouse](https://github.com/uoe-agents/robotic-warehouse) | 机器人仓库，碰撞避免，离散动作 | ⭐⭐⭐ |
| **LBF** | [semitable/lb-foraging](https://github.com/semitable/lb-foraging) | 等级约束采集，合作/竞争可切换 | ⭐⭐ |
| **TimeChamber** | [inspirai/TimeChamber](https://github.com/inspirai/TimeChamber) | Isaac Gym 自博弈，单 GPU 4096 并行 | ⭐⭐ |
| **EPyMARL** | [uoe-agents/epymarl](https://github.com/uoe-agents/epymarl) | 9 算法，Gym/SMACv2/PettingZoo 兼容 | ⭐⭐⭐⭐ |
| **Shimmy** | [Farama-Foundation/Shimmy](https://github.com/Farama-Foundation/Shimmy) | API 兼容层，将 DM/MeltingPot/OpenSpiel 转换为 PettingZoo | ⭐⭐⭐ |

---

## 4. 金融领域 MARL 环境专项发现

通过广泛搜索，我们发现了以下与金融交易直接相关的 MARL 仿真环境：

| 项目 | 机构/来源 | 核心定位 | 关联度 |
|------|-----------|----------|--------|
| **[ABIDES-MARL](https://github.com/JackBenny39/abides-marl)** | ETH Zurich / JackBenny39 | **最专业的金融 MARL 环境**，LOB 仿真，异构智能体（知情/噪声/做市商），解耦内核中断支持同步多智能体训练 | ⭐⭐⭐⭐⭐ |
| **[ABIDES](https://github.com/jpmorganchase/abides)** / [ABIDES-Gym](https://github.com/jpmorganchase/abides-jpmc-public) | [JPMorgan Chase](https://www.jpmorganchase.com/) / NSF | 高保真市场仿真，NASDAQ 风格交易所，背景智能体 | ⭐⭐⭐⭐⭐ |
| **[minABIDES](https://github.com/davebyrd/minABIDES)** | davebyrd | 轻量级多智能体市场仿真（<1000 行），历史订单回放 | ⭐⭐⭐⭐ |
| **[StockMARL](https://github.com/StockMARL)** | Nottingham | AgentPy 仿真 + DQN，异构规则型交易对手（动量/羊群/风险） | ⭐⭐⭐⭐ |
| gym-anytrading / FinRL | 开源社区 | **单智能体**为主，非 MARL | ⭐⭐ |

### 4.1 ABIDES 深度分析

[ABIDES](https://github.com/jpmorganchase/abides)（Agent-Based Interactive Discrete Event Simulation）是 **JPMorgan Chase** 与 NSF 合作开发的高保真市场仿真框架。

**核心特点**：
- **NASDAQ 风格交易所**：完整的限价订单簿（LOB）、价格-时间优先撮合、tick size、订单类型（市价/限价/止损）
- **背景智能体库**：
  - `ValueAgent`：基于基本面的估值交易
  - `NoiseAgent`：随机噪声交易（模拟散户）
  - `MarketMakerAgent`：做市商（提供双边报价）
  - `MomentumAgent`：动量跟踪
  - `AdaptiveMarketMakerAgent`：自适应做市
- **事件驱动内核**：离散事件仿真（DES），每个事件（订单到达、成交、取消）按时间戳排序处理
- **历史订单回放**：支持将真实市场数据（如 NASDAQ ITCH）回放为背景交易流

**ABIDES-MARL 扩展**：
- 在 ABIDES 基础上增加 MARL 训练支持
- 解耦内核中断：允许在仿真过程中插入 RL Agent 的决策循环
- 支持同步多智能体训练（多个 RL Agent 同时参与市场）

### 4.2 StockMARL

Nottingham 大学的 [StockMARL](https://github.com/StockMARL) 项目：
- 基于 [AgentPy](https://agentpy.readthedocs.io/) 多智能体仿真框架
- 异构规则型交易对手：动量交易者、羊群效应交易者、风险规避者
- 使用 DQN 训练智能体在规则型对手环境中获利
- 研究重点：对手建模、市场微观结构、非平稳环境下的策略适应

### 4.3 对 TradeMasterOnline 的关键启示

1. **LOB 建模**：直接借鉴 [ABIDES-MARL](https://github.com/JackBenny39/abides-marl) 的限价订单簿仿真逻辑（价格-时间优先、tick size、事件驱动内核）
2. **对手建模**：参考 [StockMARL](https://github.com/StockMARL) 的异构规则型代理 + [Neural MMO](https://github.com/NeuralMMO/client) 的市场分工机制，构建真实感交易生态
3. **背景智能体库**：设计标准化的背景交易者模板（做市商、趋势跟踪者、噪声交易者、套利者）
4. **事件驱动架构**：对于撮合引擎，事件驱动（DES）比固定时间步进更精确

---

## 5. 横向对比分析

### 5.1 定位矩阵

```
                    环境为主 ◄─────────────────────────► 训练框架为主
                    │                                       │
    通用性高        │  PettingZoo        BenchMARL         │
    （覆盖多种     │  OpenSpiel         MARLlib           │
     游戏类型）     │  Shimmy            RLlib             │
                    │                                       │
    专用性强        │  Melting Pot      VMAS/SMACv2       │
    （社会/物理）    │  ABIDES           JAXMARL           │
```

### 5.2 API 设计对比

| 框架 | 核心抽象 | 智能体迭代方式 | 观测/奖励结构 | 动作提交方式 |
|------|----------|----------------|---------------|--------------|
| [PettingZoo](https://github.com/Farama-Foundation/PettingZoo) AEC | `AECEnv` | `agent_iter()` 生成器 | `last()` 返回当前智能体 | 单智能体 `step(action)` |
| [PettingZoo](https://github.com/Farama-Foundation/PettingZoo) Parallel | `ParallelEnv` | `env.agents` 列表 | 字典 `{agent: obs}` | 字典 `{agent: action}` |
| [RLlib](https://github.com/ray-project/ray) | `MultiAgentEnv` | 用户控制 | 字典 `{agent: obs}` | 字典 `{agent: action}` |
| [OpenSpiel](https://github.com/google-deepmind/open_spiel) | `State` + `Game` | `state.current_player()` | `state.information_state()` | `state.apply_action(action)` |
| [Melting Pot](https://github.com/google-deepmind/meltingpot) | DM Lab2D API | 环境内部调度 | 以智能体为中心的网格视图 | 离散动作索引 |
| [VMAS](https://github.com/proroklab/VectorizedMultiAgentSimulator) | `Environment` + `World` | 同时步进 | `List[Tensor]` | `List[Tensor]` |
| [JAXMARL](https://github.com/FLAIROx/JaxMARL) | `MultiAgentEnv` | `Dict[str, Array]` | `Dict[str, Array]` | `Dict[str, Array]` |

### 5.3 关键特性对比

| 特性 | PettingZoo | MARLlib | Melting Pot | OpenSpiel | BenchMARL | VMAS | SMACv2 | JAXMARL |
|------|:----------:|:-------:|:-----------:|:---------:|:---------:|:----:|:------:|:-------:|
| 标准化环境 API | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ⚠️ |
| 训练算法内置 | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ |
| 分布式训练 | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | ⚠️ | ❌ |
| 社会困境专项 | ❌ | ❌ | ✅ | ⚠️ | ❌ | ❌ | ❌ | ❌ |
| 博弈论工具 | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| 零样本泛化测试 | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 向量化执行 | ⚠️ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ |
| GPU 加速 | ❌ | ❌ | ❌ | ❌ | ⚠️ | ✅ | ❌ | ✅ |
| JIT 编译 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 大规模并行 | ⚠️ | ✅ | ❌ | ❌ | ✅ | ✅ | ⚠️ | ✅ |
| 与 PyTorch 集成 | ⚠️ | ❌ | ❌ | ⚠️ | ✅ | ✅ | ⚠️ | ❌ |
| 生态兼容性 | ⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ |

### 5.4 架构模式总结

所有 MARL 框架都遵循以下**分层架构模式**：

```
┌─────────────────────────────────────────┐
│  Layer 3: Training Framework            │  ← MARLlib, BenchMARL, RLlib, JAXMARL
│  (Algorithms, Loss, Optimization)       │
├─────────────────────────────────────────┤
│  Layer 2: Environment API Standard      │  ← PettingZoo, OpenSpiel, Gymnasium
│  (Observation, Action, Step, Reset)     │
├─────────────────────────────────────────┤
│  Layer 1: Environment Implementation    │  ← 具体游戏逻辑（交易撮合、物理模拟）
│  (Game Logic, Physics, Reward)          │
├─────────────────────────────────────────┤
│  Layer 0: Vectorization / Parallelization│ ← VMAS, JAX, Ray, VectorEnv
│  (Batch Sampling, Rollout Workers)      │
└─────────────────────────────────────────┘
```

**关键洞察**：
- **[PettingZoo](https://github.com/Farama-Foundation/PettingZoo)** 定位 Layer 2（API 标准），是生态的"胶水"
- **[MARLlib](https://github.com/Replicable-MARL/MARLlib) / [RLlib](https://github.com/ray-project/ray) / [BenchMARL](https://github.com/facebookresearch/BenchMARL)** 定位 Layer 3 + Layer 0（训练 + 并行化）
- **[VMAS](https://github.com/proroklab/VectorizedMultiAgentSimulator) / [JAXMARL](https://github.com/FLAIROx/JaxMARL)** 定位 Layer 0（极致的向量化执行）
- **TradeMasterOnline** 的核心工作在 Layer 1（交易环境实现）
- 采用 PettingZoo API 可以获得最大的 Layer 3 兼容性

---

## 6. 对 TradeMasterOnline 的设计建议

### 6.1 API 选型建议：采用 PettingZoo AEC 模型

**理由**：
1. **交易天然是 AEC 模型**：订单簿撮合本质上是顺序的——先到的订单先成交。虽然交易者可以同时提交订单，但撮合引擎内部是顺序执行的
2. **智能体动态变化**：交易者可以随时进入市场或退出（开户/销户），AEC 的 `agent_iter()` 生成器天然支持这种动态性
3. **生态兼容性**：通过 PettingZoo API，训练框架的选择不受限（RLlib、TorchRL、CleanRL 等均可）
4. **观测语义清晰**：交易者的观测（订单簿切片、账户状态）作为 `last()` 的返回值，符合"等待撮合结果"的直觉

**建议的 API 草图**：

```python
class TradingEnv(AECEnv):
    def __init__(self, trading_pairs: list[TradingPairType], num_agents: int = 10):
        self.exchange = Exchange()
        self.possible_agents = [f"trader_{i}" for i in range(num_agents)]

    def reset(self, seed=None, options=None):
        self.exchange.reset()
        self.agents = self.possible_agents[:]
        self._agent_selector = agent_selector(self.agents)
        self.agent_selection = self._agent_selector.next()
        return {agent: self.observe(agent) for agent in self.agents}, {}

    def observe(self, agent):
        return {
            "order_book": self.exchange.get_order_book(),
            "portfolio": self.exchange.get_portfolio(agent),
            "market_history": self.exchange.get_recent_trades(limit=100),
        }

    def step(self, action):
        agent = self.agent_selection
        self.exchange.place_order(agent, **action)
        if self._agent_selector.is_last():
            self.exchange.match_orders()  # 撮合引擎统一结算
            self._update_rewards()
        self.agent_selection = self._agent_selector.next()

    def last(self):
        agent = self.agent_selection
        return (
            self.observe(agent),
            self._cumulative_rewards[agent],
            self.terminations[agent],
            self.truncations[agent],
            self.infos[agent],
        )
```

### 6.2 从 Melting Pot 借鉴：社会困境与零样本泛化

交易市场的核心动力学与社会困境高度相似：

| 社会困境 | 交易市场类比 |
|----------|-------------|
| Commons Harvest（过度采伐公共资源） | 流动性掠夺（大量市价单消耗订单簿深度） |
| Clean Up（污染公共环境） | 市场操纵（散布假订单制造虚假信号） |
| Prisoner's Dilemma | 做市商之间的竞争（提供流动性 vs 抢跑） |

**建议引入的评估维度**：
1. **零样本泛化**：训练好的策略面对全新类型的交易者（如从理性交易者切换到情绪化交易者）时的鲁棒性
2. **社会福利指标**：不仅评估个体 PnL，还评估市场整体质量（波动性、流动性、价格发现效率）

### 6.3 从 OpenSpiel 借鉴：信息集与不完全信息

交易是不完全信息博弈：
- 每个交易者只能看到公开订单簿（L1/L2/L3）
- 无法直接观测其他交易者的私有意图（未公开的订单、风控规则）
- 这恰好对应 OpenSpiel 的 **Information State** 概念

**建议**：将交易者的观测建模为信息集，而非全局状态。这有助于：
- 更真实地模拟市场信息不对称
- 研究信息优势对策略表现的影响
- 应用 CFR 类算法计算近似均衡

### 6.4 从 BenchMARL 借鉴：标准化基准测试

交易策略评估的最大痛点是**不可比性**。建议：

1. **固定市场参数配置**：
   - 初始价格、波动率、流动性深度
   - 智能体数量、初始资金分布
   - 观测窗口长度、动作粒度

2. **分层评估指标**：
   - 个体层面：PnL、夏普比率、最大回撤、胜率
   - 市场层面：价格波动率、买卖价差、成交量分布
   - 社会层面：基尼系数（财富不平等）、市场稳定性

3. **配置驱动实验**：
   ```yaml
   market:
     initial_price: 50000.0
     volatility: 0.02
   agents:
     num_traders: 10
     initial_balance: 100000  # USDT
   evaluation:
     episodes: 1000
     metrics: [pnl, sharpe, max_drawdown, market_impact]
   ```

### 6.5 从 MARLlib 借鉴：CTDE 架构适配

交易场景天然适合 **CTDE（Centralized Training Decentralized Execution）**：

- **训练阶段**：可以访问全局状态（完整订单簿、所有交易者的历史行为），用于训练 centralized critic
- **执行阶段**：每个交易者只能基于局部观测（自己的持仓、订单簿切片）做决策

**关键设计**：
- `state()` 方法返回全局市场状态（用于 critic）
- `observe(agent)` 返回局部观测（用于 actor）
- 奖励函数需要仔细设计：个体 PnL 可能导致恶性竞争，需要引入市场质量惩罚项

### 6.6 从 VMAS / JAXMARL 借鉴：向量化执行

对于大规模策略回测和超参数搜索：
- 采用 **VMAS 式向量化架构**：通过 PyTorch batch 维度并行多个回测窗口
- 长期考虑 **JAX 重写核心撮合引擎**：可获得 1000x-10000x 吞吐提升
- 参考 SocialJAX 的思路，将订单簿状态表示为紧凑数组而非对象，在 GPU 上并行运行

### 6.7 从 ABIDES 借鉴：事件驱动与背景智能体

- **事件驱动内核（DES）**：撮合引擎应采用离散事件驱动而非固定时间步进，精确处理订单到达、成交、取消
- **背景智能体库**：设计标准化的背景交易者模板（做市商、趋势跟踪者、噪声交易者、套利者）
- **历史订单回放**：支持将真实市场数据回放为背景交易流，提升仿真真实性

---

## 7. 参考资料

### 论文

1. Terry, J. K., et al. (2020). [*PettingZoo: Gym for Multi-Agent Reinforcement Learning*](https://arxiv.org/abs/2009.14471). arXiv:2009.14471.
2. Hu, S., et al. (2022). [*MARLlib: A Scalable and Efficient Library For Multi-agent Reinforcement Learning*](https://arxiv.org/abs/2210.13708). arXiv:2210.13708.
3. Leibo, J. Z., et al. (2021). [*Melting Pot: multi-agent reinforcement learning for artificial societies*](https://arxiv.org/abs/2107.06875). arXiv:2107.06875.
4. Lanctot, M., et al. (2019). [*OpenSpiel: A Framework for Reinforcement Learning in Games*](https://arxiv.org/abs/1908.09453). arXiv:1908.09453.
5. Bettini, M., et al. (2023). [*BenchMARL: Benchmarking Multi-Agent Reinforcement Learning*](https://arxiv.org/abs/2312.01472). arXiv:2312.01472.
6. Rutherford, A., et al. (2023). [*JAXMARL: Multi-Agent RL Environments in JAX*](https://arxiv.org/abs/2311.10083). arXiv:2311.10083.
7. Byrd, D., et al. (2019). [*ABIDES: Towards High-Fidelity Market Simulation for AI Training*](https://arxiv.org/abs/1904.12066). arXiv:1904.12066.

### 官方文档与仓库

| 框架 | 文档 | GitHub |
|------|------|--------|
| PettingZoo | [pettingzoo.farama.org](https://pettingzoo.farama.org/) | [Farama-Foundation/PettingZoo](https://github.com/Farama-Foundation/PettingZoo) |
| MARLlib | [marllib.readthedocs.io](https://marllib.readthedocs.io/) | [Replicable-MARL/MARLlib](https://github.com/Replicable-MARL/MARLlib) |
| Melting Pot | — | [google-deepmind/meltingpot](https://github.com/google-deepmind/meltingpot) |
| OpenSpiel | [openspiel.readthedocs.io](https://openspiel.readthedocs.io/) | [google-deepmind/open_spiel](https://github.com/google-deepmind/open_spiel) |
| BenchMARL | [facebookresearch.github.io/BenchMARL](https://facebookresearch.github.io/BenchMARL/) | [facebookresearch/BenchMARL](https://github.com/facebookresearch/BenchMARL) |
| RLlib | [docs.ray.io/rllib](https://docs.ray.io/en/latest/rllib/index.html) | [ray-project/ray](https://github.com/ray-project/ray) |
| VMAS | — | [proroklab/VectorizedMultiAgentSimulator](https://github.com/proroklab/VectorizedMultiAgentSimulator) |
| SMACv2 | — | [oxwhirl/smacv2](https://github.com/oxwhirl/smacv2) |
| JAXMARL | — | [FLAIROx/JaxMARL](https://github.com/FLAIROx/JaxMARL) |
| Shimmy | [shimmy.farama.org](https://shimmy.farama.org/) | [Farama-Foundation/Shimmy](https://github.com/Farama-Foundation/Shimmy) |
| SuperSuit | — | [Farama-Foundation/SuperSuit](https://github.com/Farama-Foundation/SuperSuit) |
| ABIDES | — | [jpmorganchase/abides](https://github.com/jpmorganchase/abides) |
| ABIDES-MARL | — | [JackBenny39/abides-marl](https://github.com/JackBenny39/abides-marl) |
| Neural MMO | [neuralmmo.github.io](https://neuralmmo.github.io/) | [NeuralMMO/client](https://github.com/NeuralMMO/client) |
| MAgent2 | — | [Farama-Foundation/MAgent2](https://github.com/Farama-Foundation/MAgent2) |
| SocialJAX | — | [DarylRodrigo/SocialJAX](https://github.com/DarylRodrigo/SocialJAX) |

### 相关项目

- [Overcooked-AI](https://github.com/HumanCompatibleAI/overcooked_ai)
- [Google Research Football](https://github.com/google-research/football)
- [RWARE](https://github.com/uoe-agents/robotic-warehouse)
- [LBF](https://github.com/semitable/lb-foraging)
- [TimeChamber](https://github.com/inspirai/TimeChamber)
- [EPyMARL](https://github.com/uoe-agents/epymarl)
- [minABIDES](https://github.com/davebyrd/minABIDES)

---

*报告生成时间：2026-05-24*
*基于各框架 master/main 分支的实际源代码阅读*
