# TradeMasterOnline 开发者手册

本手册是面向开发者的内部文档，帮助理解系统架构、快速上手开发和扩展功能。

## 手册结构

| 文档 | 内容 | 适合读者 |
|------|------|----------|
| [architecture.md](./architecture.md) | 系统架构概览、模块职责、核心数据流、关键设计决策 | 所有新加入的开发者 |
| [core_modules.md](./core_modules.md) | 核心模块详解：订单模型、订单簿、撮合引擎、配置系统 | 需要修改核心逻辑的开发者 |
| [trading_env.md](./trading_env.md) | AEC 交易环境：观测/动作空间、step 流程、资金冻结、手续费结算 | 需要对接训练算法或扩展环境的开发者 |
| [extension_guide.md](./extension_guide.md) | 扩展指南：自定义奖励、新增订单类型、修改 Filter 等 | 需要二次开发的开发者 |

## 项目定位

TradeMasterOnline 是一个基于 [PettingZoo](https://pettingzoo.farama.org/) AEC API 的多智能体交易仿真环境。

- **不是**交易所后端：不做持久化、不做网络通信、不做高并发优化
- **不是**训练框架：不提供 PPO、QMIX 等算法，仅提供环境
- **是**可配置、可扩展的仿真平台：支持多资产限价订单簿、撮合引擎、Binance 风格手续费模型

## 技术栈

- **Python 3.14**（完整类型注解）
- **Pydantic v2**（配置模型与订单数据校验）
- **PettingZoo**（AEC 多智能体环境接口）
- **Gymnasium**（spaces 定义）
- **pytest + ruff + ty**（测试、格式化、类型检查）

## 阅读顺序建议

1. 先读 [architecture.md](./architecture.md) 建立整体认知
2. 再读 [core_modules.md](./core_modules.md) 理解撮合和订单簿细节
3. 最后按需查阅 [trading_env.md](./trading_env.md) 和 [extension_guide.md](./extension_guide.md)

## 与代码保持同步

Manual 是**活文档**。任何涉及架构、接口、行为变更的代码修改完成后，都应同步更新对应章节。若发现文档与代码不符，**以代码为准**。
