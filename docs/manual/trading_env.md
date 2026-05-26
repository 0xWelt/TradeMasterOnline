# AEC 交易环境详解

`TradingEnv` 继承自 `pettingzoo.utils.env.AECEnv`，实现多智能体序贯交易仿真。

## 观测空间

`observe(agent)` 返回每个 agent 的局部观测：

```python
{
    'books': {
        'BTC/USDT': {
            'bids': ndarray(shape=(n_levels, 2)),  # [[price, qty], ...]
            'asks': ndarray(shape=(n_levels, 2)),
        },
        'ETH/USDT': {
            'bids': ndarray(shape=(n_levels, 2)),
            'asks': ndarray(shape=(n_levels, 2)),
        },
    },
    'holdings': {
        'BTC': np.float64(1.0),
        'ETH': np.float64(10.0),
        'USDT': np.float64(100000.0),
    },
}
```

### 订单簿快照

- 每个交易对返回前 `n_levels` 档的聚合数据（价格 + 总量）
- 快照按 `get_snapshot(n_levels)` 获取，若某方向档位数不足，用 0 填充到固定形状 `(n_levels, 2)`
- **不含订单粒度信息**：agent 看不到订单簿中单个订单的归属，仅能看到聚合后的价格档

### 持仓

- 仅包含当前 agent 自己的持仓（看不到其他 agent 的持仓）
- 以 `np.float64` 包装，与 Gymnasium `spaces.Box` 兼容

### 不完全信息设计

观测空间的设计刻意隐藏以下信息，形成不完全信息博弈：
- 其他 agent 的持仓
- 订单簿中单个订单的归属（哪个 agent 下的单）
- 未成交挂单的具体数量和价格分布（仅能看到前 n 档聚合）

## 动作空间

`step(action)` 接收的 `action` 是一个字典：

```python
{
    'asset_id': 0,        # 交易对索引（离散，0 ~ n_pairs-1）
    'side': 1,            # 0=HOLD, 1=BUY, 2=SELL（离散）
    'price': 50000.0,     # 限价（连续 float）
    'quantity': 0.1,      # 数量（连续 float）
}
```

### 动作语义

| `side` | 行为 | 资产变化 |
|--------|------|----------|
| `0` (HOLD) | 不创建订单，直接推进 | 无 |
| `1` (BUY) | 创建限价买单 | 冻结 quote，成交后增加 base |
| `2` (SELL) | 创建限价卖单 | 冻结 base，成交后增加 quote |

### 连续值离散化

`price` 和 `quantity` 为连续 float，但环境不自动离散化。外部训练算法需自行将离散动作映射到连续价格/数量（例如：从动作空间采样后乘以一个缩放系数）。

## Step 执行流程

`step(action)` 的完整执行流程：

```
1. 空 agent / 已终止 agent → 跳过
2. action is None → 直接返回
3. 解析动作：side = [HOLD, BUY, SELL][action['side']]

4. 若 side == HOLD：
   → 无状态变化，直接推进到下一 agent

5. 若 side == BUY 或 SELL：
   a. Filter 校验（参考 Binance）
      - _is_valid_step(price, tick_size) → 失败则 REJECTED
      - _is_valid_step(qty, step_size) → 失败则 REJECTED
      - price * qty >= min_notional → 失败则 REJECTED

   b. 资金检查（_can_place_order）
      - BUY：检查 quote 资产可用余额 >= price * qty
      - SELL：检查 base 资产可用余额 >= qty
      - 可用余额 = holdings - 该资产维度所有未成交挂单冻结额
      - 不足则 REJECTED

   c. 创建订单（Order, GTC）
      - order_id = f'{agent}_{counter}'
      - stp_mode = pair.default_stp_mode

   d. 撮合（OrderBook.place_order）
      - Matcher.match() 执行价格优先时间优先撮合
      - 返回 Trade 列表

   e. 结算（_settle_trades）
      - 按 Binance received-asset 模式更新 holdings
      - 手续费精度截断后累加到 exchange_holdings

6. 终止检查（_check_terminal）
   - step_count >= max_steps → 所有 agent truncation = True
   - check_negative_equity and equity <= 0 → termination = True

7. 推进（_advance_agent）
   - 按轮询顺序切换到下一个存活 agent
```

## 资金冻结机制

### 冻结模型

参考 Binance Spot 的 `free` / `locked` 余额模型：

- `holdings`：该 agent 的某资产总余额（free + locked）
- `locked`：被未成交订单冻结的余额
- `free = holdings - locked`：可用于新订单的可用余额

### 全局统计

`_can_place_order` 在检查余额时，遍历**所有交易对**的订单簿，按资产维度全局统计：

**BUY 场景**：
```python
locked = sum(
    o.price * o.quantity
    for book in self.books.values()
    for o in book.orders.values()
    if o.agent_id == agent and o.side is Side.BUY and pair.quote == quote_asset
)
available = self.holdings[agent].get(quote_asset, 0.0)
return available - locked >= price * qty
```

**SELL 场景**：
```python
locked = sum(
    o.quantity
    for book in self.books.values()
    for o in book.orders.values()
    if o.agent_id == agent and o.side is Side.SELL and pair.base == base_asset
)
available = self.holdings[agent].get(base_asset, 0.0)
return available - locked >= qty
```

### 关键特性

- **跨交易对共享**：同一 quote 资产（如 USDT）在 BTC/USDT 和 ETH/USDT 中共享资金池
- **不预扣手续费**：检查余额时不预留手续费，因为手续费在成交后才从 received asset 扣除
- **允许双向挂单**：同一 agent 可以在同一交易对同时挂买单和卖单（冻结不冲突）

## 手续费结算

### Binance received-asset 模式

手续费从**收到的资产**中扣除：

| 角色 | 付出 | 收到（扣除手续费后） |
|------|------|---------------------|
| BUY Taker | `notional` in quote | `qty * (1 - taker_fee)` in base |
| BUY Maker | `notional` in quote | `qty * (1 - maker_fee)` in base |
| SELL Taker | `qty` in base | `notional * (1 - taker_fee)` in quote |
| SELL Maker | `qty` in base | `notional * (1 - maker_fee)` in quote |

### 精度截断

手续费和收到金额按精度截断（truncate，非四舍五入）：

```python
def _trunc(value: float, precision: int) -> float:
    factor = 10 ** precision
    return int(value * factor) / factor
```

### 资产守恒

所有 agent 的持仓 + `exchange_holdings`（交易所累计手续费）= 初始资产总量。该不变量在 `tests/examples/test_random_agents.py` 中被断言验证。

## 终止条件

### Truncation（截断）

当 `step_count >= config.env.max_steps` 时，所有存活 agent 的 `truncations` 被设为 `True`。AEC 语义下，truncation 表示 episode 因步数限制正常结束，不表示 agent "死亡"。

### Termination（终止）

当 `config.env.check_negative_equity = True` 且某 agent 的净资产 `<= 0` 时，该 agent 的 `terminations` 被设为 `True`。agent 被终止后不再参与后续 step，但其已有订单仍保留在订单簿中（可被其他 agent 撮合）。

### 净资产计算

```python
def _equity(self, agent: AgentId) -> float:
    total = 0.0
    for sym, qty in self.holdings[agent].items():
        price = self.prices.get(sym, 0.0)
        total += qty * price
    return total
```

按最新成交价估算。计价资产（如 USDT）的价格固定为 `1.0`。

## AEC API 映射

| AEC 方法 | 说明 |
|----------|------|
| `reset(seed, options)` | 重置环境：初始化订单簿、价格、持仓、AEC 状态 |
| `step(action)` | 执行当前 agent 的动作（见上文完整流程） |
| `observe(agent)` | 返回指定 agent 的局部观测 |
| `last()` | 返回 `(observation, reward, termination, truncation, info)` |
| `agent_selection` | 当前待行动的 agent 名称 |
| `agents` | 当前存活 agent 列表 |
| `possible_agents` | 所有可能的 agent 名称（`reset()` 后固定） |

### 奖励

MVP 阶段 `reward` 恒为 `0.0`。外部训练算法可通过 `observe()` 获取完整状态后自行计算奖励（如持仓市值变化、夏普比率等）。

### 状态（state）

`state()` 当前抛出 `NotImplementedError`。如需 CTDE（Centralized Training with Decentralized Execution）的全局状态，可扩展为返回所有 agent 的完整持仓 + 所有订单簿的内部状态。
