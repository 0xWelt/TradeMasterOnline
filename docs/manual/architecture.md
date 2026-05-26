# 系统架构概览

## 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      TradingEnv (AECEnv)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ 观测空间     │  │ 动作空间     │  │  Step 执行流程       │  │
│  │ (books +    │  │ (asset_id,  │  │  Filter → 资金检查   │  │
│  │  holdings)  │  │  side,      │  │  → 撮合 → 结算       │  │
│  │             │  │  price, qty)│  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │ place_order / cancel_order
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      OrderBook (per pair)                   │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │  _bids: dict    │  │  _asks: dict    │  _orders: dict   │
│  │  price→Level    │  │  price→Level    │  order_id→Order │
│  └─────────────────┘  └─────────────────┘                   │
└────────────────────┬────────────────────────────────────────┘
                     │ match(order, book)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                         Matcher                             │
│              价格优先、时间优先 + STP 自成交保护               │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    ConfigSchema (YAML)                      │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌───────────────┐  │
│  │ Exchange│  │  Agent  │  │   Env   │  │  Assets/Fees  │  │
│  │ Config  │  │ Config  │  │ Config  │  │     ...       │  │
│  └─────────┘  └─────────┘  └─────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 模块职责

### `tmo.config` — 配置解析

- **入口**：`ConfigSchema.from_yaml(path)`
- **职责**：将 YAML 配置文件解析为强类型的 Pydantic 模型，执行交叉校验（如交易对引用的资产必须存在于资产列表）
- **关键类**：`ConfigSchema`、`ExchangeConfig`、`AgentConfig`、`EnvConfig`

### `tmo.core` — 核心交易引擎

- **职责**：订单数据模型、限价订单簿维护、价格优先时间优先撮合
- **无外部依赖**：`core` 模块不依赖 `env` 或 `config`，可独立测试和使用
- **关键类**：
  - `Order` / `Trade`：Pydantic frozen 数据模型
  - `Side` / `TimeInForce` / `OrderStatus`：StrEnum 枚举
  - `OrderBook`：单个交易对的完整订单簿
  - `PriceLevel`：同一价格的 FIFO 队列
  - `Matcher`：撮合引擎

### `tmo.env` — AEC 交易环境

- **入口**：`TradingEnv(config)` 或 `TradingEnv.from_config(path)`
- **职责**：实现 PettingZoo AEC 接口，将核心引擎包装为可交互的强化学习环境
- **关键类**：`TradingEnv(AECEnv)`
- **关键方法**：`reset()`、`step(action)`、`observe(agent)`、`last()`

### `tmo.utils` — 工具类型

- **职责**：类型别名，提升核心模块类型注释可读性
- **内容**：`AgentId = str`、`OrderId = str`、`PairId = str`、`AssetSymbol = str`

## 核心数据流

一次完整的 `step(action)` 执行以下流程：

```
1. 解析动作
   action = {'asset_id': 0, 'side': 1, 'price': 50000.0, 'quantity': 0.1}
   → pair = BTC/USDT, side = BUY

2. Filter 校验（参考 Binance）
   → price % tick_size == 0?
   → qty % step_size == 0?
   → price * qty >= min_notional?
   任一失败：创建 REJECTED 订单，直接返回

3. 资金检查（_can_place_order）
   → 遍历所有交易对，统计该 agent 同一 quote 资产的未成交买单冻结额
   → free = holdings - locked
   → free >= price * qty?
   不足：创建 REJECTED 订单，直接返回

4. 创建限价订单（Order, GTC）
   → 调用 OrderBook.place_order()

5. 撮合（Matcher.match）
   → 价格优先、时间优先匹配对手方
   → 自成交保护（STP）：取消 resting order，继续撮合
   → 返回 Trade 列表 + 剩余数量

6. 结算（_settle_trades）
   → 按 Binance received-asset 模式扣除手续费
   → 更新双方 holdings
   → 更新 prices[base] = 最新成交价

7. 推进（_advance_agent）
   → 切换到下一个存活 agent

8. 终止检查（_check_terminal）
   → step_count >= max_steps? → truncation
   → check_negative_equity and equity <= 0? → termination
```

## 关键设计决策

### 1. 为什么选 PettingZoo AEC（Agent Environment Cycle）

PettingZoo 提供两种 API：AEC（序贯）和 Parallel（并行）。本环境选择 AEC 是因为：

- **交易天然序贯**：真实交易所中订单按到达时间先后处理，AEC 的逐个 agent 执行语义与限价单撮合机制天然匹配
- **动作即时生效**：每个 `step()` 处理一个 agent 的一笔订单，订单立即进入订单簿并可能触发成交，下一 agent 看到的是已更新的市场状态
- **部分可观测**：AEC 支持每个 agent 拥有独立观测，`observe(agent)` 仅返回该 agent 的持仓和订单簿快照

### 2. 为什么用 Pydantic 数据模型

- **类型安全**：`Order`、`Trade` 及所有配置模型均用 Pydantic `BaseModel` 定义，带完整类型注解
- **运行时校验**：`Field(gt=0)`、`model_validator` 等机制在对象创建时即校验约束，避免无效数据流入核心引擎
- **不可变性**：`Order` 和 `Trade` 设置 `frozen=True`，订单一旦创建不可修改，符合交易所订单不可变的业务语义

### 3. Binance received-asset 手续费模式

参考 Binance 主流现货交易所的实现：

- **手续费从收到的资产中扣除**，不增加支付资产的开销
- BUY taker：支付 exact notional（quote），收到 `qty * (1 - taker_fee)`（base）
- SELL taker：付出 exact qty（base），收到 `notional * (1 - taker_fee)`（quote）
- 不预扣手续费：`_can_place_order` 检查余额时不预留手续费，因为手续费在成交后才扣除

这种设计保证了资产守恒：所有 agent 持仓 + 交易所手续费累计 = 初始总量。

### 4. 全局资金冻结（跨交易对按资产维度）

参考 Binance `free` / `locked` 余额模型：

- 同一 **quote** 资产（如 USDT）在所有交易对中共享一个资金池
- 同一 **base** 资产（如 BTC）在所有交易对中也共享一个资金池
- `_can_place_order` 遍历**所有交易对**的订单簿，按资产维度全局统计冻结占用
- 允许同交易对双向挂单：一个 agent 可以同时持有某交易对的未成交买单和卖单

### 5. 奖励恒为 0

MVP 阶段环境不定义奖励函数，`step()` 中设置 `self.rewards[agent] = 0.0`。理由：

- 奖励设计高度依赖具体研究目标（持仓市值变化、已实现盈亏、夏普比率等）
- 环境仅负责状态转移和撮合逻辑，奖励留给外部训练算法自定义
- 外部算法可通过 `observe()` 获取完整状态，自行计算奖励
