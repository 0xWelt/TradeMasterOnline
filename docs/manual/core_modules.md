# 核心模块详解

## 订单模型 (`tmo/core/order.py`)

### 枚举类型

#### `Side` — 交易方向

```python
class Side(StrEnum):
    HOLD = 'HOLD'   # 观望，不创建订单
    BUY = 'BUY'     # 买入 base 资产
    SELL = 'SELL'   # 卖出 base 资产
```

`HOLD` 是动作空间中的 `side=0`，表示该 step 不进行交易。环境收到 `HOLD` 时直接推进到下一 agent，无任何状态变化。

#### `TimeInForce` — 订单有效期

```python
class TimeInForce(StrEnum):
    GTC = 'GTC'   # Good Till Cancelled：一直有效直到取消（默认）
    IOC = 'IOC'   # Immediate or Cancel：立即成交，剩余取消
    FOK = 'FOK'   # Fill or Kill：全部成交否则取消
```

MVP 阶段所有订单默认 `GTC`。`IOC` 和 `FOK` 的枚举已定义，但引擎暂未实现其特殊处理逻辑（未来在 `OrderBook.place_order` 中根据 `time_in_force` 字段区分处理）。

#### `OrderStatus` — 订单生命周期

```python
class OrderStatus(StrEnum):
    NEW = 'NEW'
    PARTIALLY_FILLED = 'PARTIALLY_FILLED'
    FILLED = 'FILLED'
    CANCELED = 'CANCELED'
    EXPIRED = 'EXPIRED'
    REJECTED = 'REJECTED'
```

状态转移：
- `NEW` → `PARTIALLY_FILLED`（部分成交）→ `FILLED`（完全成交）
- `NEW` → `CANCELED`（用户撤单）
- `NEW` → `EXPIRED`（IOC/FOK 未完全成交，或 STP 触发）
- `NEW` → `REJECTED`（Filter 失败或余额不足）

### `Order` — 限价订单

```python
class Order(BaseModel):
    model_config = {'frozen': True}

    order_id: OrderId       # 全局唯一订单标识
    agent_id: AgentId       # 下单者标识
    pair_id: PairId         # 交易对标识（如 BTC/USDT）
    side: Side              # BUY / SELL
    price: float = Field(gt=0)
    quantity: float = Field(gt=0)
    time_in_force: TimeInForce = TimeInForce.GTC
    stp_mode: str | None = None   # None 表示使用交易对默认值
    status: OrderStatus = OrderStatus.NEW
    filled_qty: float = 0.0
```

**设计要点**：
- `frozen=True`：订单一旦创建不可修改。部分成交时引擎会创建新的 `Order` 实例替换旧实例，而不是原地修改 `quantity` 和 `filled_qty`
- `stp_mode`：覆盖交易对默认的 STP 策略。`None` 时使用 `PairConfig.default_stp_mode`
- `status` 和 `filled_qty`：在 `Matcher` 中根据成交情况更新，但更新方式是通过创建新的 `Order` 实例

### `Trade` — 成交记录

```python
class Trade(BaseModel):
    model_config = {'frozen': True}

    pair_id: PairId
    price: float = Field(gt=0)
    quantity: float = Field(gt=0)
    buyer_id: AgentId
    seller_id: AgentId
    buy_order_id: OrderId
    sell_order_id: OrderId
```

**约束**：`Trade` 创建时通过 `model_validator` 校验 `buyer_id != seller_id`，从数据层面禁止自成交记录入库。

**notional 属性**：`price * quantity`，在 `_settle_trades` 中用于计算手续费。

---

## 订单簿 (`tmo/core/order_book.py`)

### `PriceLevel` — 同一价格的 FIFO 队列

```python
class PriceLevel:
    def __init__(self, price: float) -> None:
        self.price = price
        self.orders: deque[Order] = deque()
        self.total_qty = 0.0
```

- `orders`：按时间顺序排列的双端队列，支持 `append`（尾部追加）、`popleft`（头部取出）、`appendleft`（头部插入，用于部分成交后放回）
- `total_qty`：该价格档的累计数量，在 `append`/`popleft`/`remove` 时同步更新
- `remove(order_id)`：按 `order_id` 遍历队列移除指定订单，时间复杂度 O(n)。因单个价格档的订单数量通常有限，该复杂度可接受

### `OrderBook` — 单个交易对的完整订单簿

```python
class OrderBook:
    def __init__(self, pair_id: PairId) -> None:
        self.pair_id = pair_id
        self._bids: dict[float, PriceLevel] = {}   # 买单队列
        self._asks: dict[float, PriceLevel] = {}   # 卖单队列
        self._orders: dict[str, Order] = {}        # order_id 索引
        self._matcher = Matcher()
```

**核心 API**：

| 方法 | 说明 |
|------|------|
| `place_order(order, stp_mode)` | 挂单并撮合，返回 `list[Trade]`。若有剩余未成交，作为 resting order 挂入订单簿 |
| `cancel_order(order_id)` | 撤单，返回被撤的 `Order` 或 `None` |
| `get_agent_outstanding(agent_id, side)` | 返回 agent 在指定方向上的未成交挂单总量 |
| `get_snapshot(n_levels=5)` | 返回前 n 档的 `(价格, 总量)` 快照，格式 `{'bids': [...], 'asks': [...]}` |

**内部逻辑**：

`place_order` 的执行流程：
1. 将订单加入 `_orders` 索引
2. 调用 `Matcher.match()` 撮合
3. 若有剩余数量，创建新的 resting `Order` 并挂入对应方向的 `_bids` 或 `_asks`
4. 若完全成交，从 `_orders` 中移除

---

## 撮合引擎 (`tmo/core/matcher.py`)

### `Matcher.match()`

```python
def match(
    self, order: Order, book: OrderBook, stp_mode: str = 'expire_maker'
) -> tuple[list[Trade], float]:
    """返回 (成交列表, 剩余未成交数量)。"""
```

### 撮合算法

**BUY 订单**：从最低 ask 价格开始匹配，要求 `ask_price <= order.price`。同一价格档内按 FIFO 顺序匹配。

**SELL 订单**：从最高 bid 价格开始匹配，要求 `bid_price >= order.price`。同一价格档内按 FIFO 顺序匹配。

### 自成交保护（STP）

当 incoming order 与 resting order 属于同一 agent 时，根据 `stp_mode` 处理：

| 策略 | 行为 |
|------|------|
| `expire_maker` | 取消 resting order（被动方），incoming 继续撮合 |
| `expire_taker` | 取消 incoming order（主动方），resting 保留 |
| `expire_both` | 两边同时取消 |
| `none` | 跳过该 resting order，尝试同一价格档的下一个订单 |

**默认策略**：`expire_maker`（参考 Binance / QFEX 默认行为）。

### 部分成交

当成交数量 `qty < resting.quantity` 时：
1. 创建更新后的 `Order` 实例：`quantity = resting.quantity - qty`，`filled_qty += qty`，`status = PARTIALLY_FILLED`
2. 将该更新后的订单 `appendleft` 放回队列头部（保持其在当前价格档的优先级）
3. 同步更新 `level.total_qty`

---

## 配置系统 (`tmo/config/schema.py`)

### 配置模型层级

```
ConfigSchema
├── exchange: ExchangeConfig
│   ├── assets: list[AssetConfig]      # [{symbol: 'BTC'}, ...]
│   ├── pairs: list[PairConfig]        # [{id, base, quote, initial_price, ...}, ...]
│   └── fees: FeeConfig                # {maker_fee, taker_fee, base_precision, quote_precision}
├── agents: AgentConfig
│   ├── n_agents: int
│   ├── initial_holdings: dict | list[dict]
│   └── max_qty: float
└── env: EnvConfig
    ├── max_steps: int
    └── check_negative_equity: bool
```

### 关键字段说明

#### `PairConfig`

| 字段 | 说明 |
|------|------|
| `initial_price` | 该交易对 base 资产的初始价格（以 quote 计价） |
| `tick_size` | 价格步长，`step()` 中校验 `price % tick_size == 0` |
| `step_size` | 数量步长，`step()` 中校验 `qty % step_size == 0` |
| `min_notional` | 最小名义价值，`step()` 中校验 `price * qty >= min_notional` |
| `n_levels` | 订单簿观测档位数，影响 `observe()` 返回的数组形状 |
| `default_stp_mode` | 默认自成交保护策略，可选 `expire_maker` / `expire_taker` / `expire_both` / `none` |

#### `AgentConfig.initial_holdings`

支持两种格式：

- **统一 dict**（所有 agent 相同）：`{'BTC': 1.0, 'USDT': 100000.0}`
- **per-agent list**（差异化持仓）：`[{'BTC': 2.0, ...}, {'BTC': 1.0, ...}, ...]`，长度必须等于 `n_agents`

#### `FeeConfig`

- `maker_fee` / `taker_fee`：手续费率，必须 `>= 0`
- `base_precision` / `quote_precision`：精度截断位数，`_settle_trades` 中用 `int(value * 10^precision) / 10^precision` 截断

### 交叉校验

`ExchangeConfig` 和 `AgentConfig` 各有一个 `model_validator`：

1. `_check_assets_referenced`：验证所有交易对的 `base` 和 `quote` 都存在于 `assets` 列表中
2. `_check_holdings_length`：当 `initial_holdings` 为 `list` 时，验证长度等于 `n_agents`

### 加载配置

```python
from tmo.config.schema import ConfigSchema

# 从 YAML 文件加载
env = TradingEnv.from_config('examples/configs/default.yaml')

# 或从字典加载
config = ConfigSchema.model_validate({...})
env = TradingEnv(config)
```
