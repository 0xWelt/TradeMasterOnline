# 开发者扩展指南

## 添加新交易对

**修改范围**：仅 YAML 配置文件，无需改代码。

在 `exchange.pairs` 列表中新增条目：

```yaml
exchange:
  assets:
    - symbol: "SOL"      # 新增资产需先声明

  pairs:
    - id: "SOL/USDT"
      base: "SOL"
      quote: "USDT"
      initial_price: 150.0
      tick_size: 0.01
      step_size: 0.001
      min_notional: 10.0
      n_levels: 5
      default_stp_mode: "expire_maker"
```

配置系统的 `model_validator` 会自动校验 `base` 和 `quote` 是否存在于 `assets` 列表中。

## 自定义奖励函数

MVP 阶段环境 `reward` 恒为 `0.0`。自定义奖励由外部训练算法实现：

```python
env = TradingEnv.from_config('config.yaml')
env.reset()

for agent in env.agent_iter():
    obs, reward, termination, truncation, info = env.last()

    # 自定义奖励：持仓市值变化
    equity = sum(
        env.holdings[agent].get(sym, 0.0) * env.prices.get(sym, 0.0)
        for sym in env._asset_symbols
    )
    custom_reward = equity - prev_equity[agent]

    action = policy(obs, custom_reward)
    env.step(action)
```

**设计原则**：环境负责状态转移和撮合，奖励定义留给外部，避免环境耦合具体研究目标。

## 修改 STP 策略

STP 策略可在两个层面配置：

### 1. 交易对默认策略（YAML 配置）

```yaml
pairs:
  - id: "BTC/USDT"
    default_stp_mode: "expire_taker"   # 或 expire_both / none
```

### 2. 单笔订单覆盖

创建 `Order` 时传入 `stp_mode` 字段覆盖默认值：

```python
order = Order(
    ..., stp_mode='expire_both'
)
trades = book.place_order(order, stp_mode='expire_both')
```

**引擎支持的所有策略**：`expire_maker`（默认）、`expire_taker`、`expire_both`、`none`。详见 [core_modules.md](./core_modules.md#自成交保护stp)。

## 扩展订单类型

当前仅支持限价单（Limit Order）。扩展思路：

### 市价单（Market Order）

市价单可视为以极端价格提交的限价单：
- BUY market：以 `np.inf` 价格创建 BUY 限价单，确保匹配所有 ask
- SELL market：以 `0` 价格创建 SELL 限价单，确保匹配所有 bid

实现方式：在 `TradingEnv.step()` 中根据 `side` 标志判断是否为市价单，自动设置极端价格后走现有限价单逻辑。

### 止损单 / 止盈单（Stop-Loss / Take-Profit）

需要扩展 `Order` 模型增加 `trigger_price` 字段：

```python
class Order(BaseModel):
    ...
    trigger_price: float | None = None   # 触发价格
    order_type: str = 'LIMIT'            # LIMIT / STOP_LOSS / TAKE_PROFIT
```

在 `TradingEnv.step()` 或独立的 `_process_conditional_orders()` 中，每轮检查条件单触发条件（如最新成交价突破 `trigger_price`），触发后转为普通限价单进入订单簿。

### OCO（One Cancels Other）

需要扩展 `OrderBook` 维护 OCO 组关系：

```python
class OrderBook:
    def __init__(...):
        ...
        self._oco_groups: dict[str, list[str]] = {}   # group_id -> [order_id, ...]
```

当 OCO 组中任一订单成交或被取消时，自动取消组内其他订单。

## 添加 Filter 规则

当前 `TradingEnv.step()` 已实现三种 Filter：

1. `PRICE_FILTER`：`price` 必须是 `tick_size` 的整数倍
2. `LOT_SIZE`：`quantity` 必须是 `step_size` 的整数倍
3. `MIN_NOTIONAL`：`price * quantity >= min_notional`

参考 Binance，可扩展的 Filter：

### 最大订单数量（MAX_NUM_ORDERS）

限制单个 agent 在同一交易对上的未成交挂单数量：

```python
# 在 _can_place_order 或 step() 中添加
current_orders = sum(
    1 for o in book.orders.values()
    if o.agent_id == agent
)
if current_orders >= pair.max_num_orders:
    # REJECTED
```

### 最大名义价值（MAX_NOTIONAL）

限制单笔订单的最大名义价值：

```python
if price * qty > pair.max_notional:
    # REJECTED
```

###  Iceberg 订单（冰山单）

扩展 `Order` 模型增加 `visible_qty` 和 `hidden_qty` 字段，在 `PriceLevel` 中仅展示 `visible_qty`，每次成交后从 `hidden_qty` 补充。

## 扩展观测空间

### 添加私有订单信息

当前观测仅包含聚合订单簿快照。如需让 agent 看到**自己的未成交挂单**（类似交易所的 "Open Orders" 接口）：

```python
def observe(self, agent: AgentId) -> dict[str, Any]:
    obs = {...}  # 现有观测

    # 添加 agent 的未成交挂单
    my_orders = []
    for book in self.books.values():
        for order in book.orders.values():
            if order.agent_id == agent:
                my_orders.append({
                    'pair_id': order.pair_id,
                    'side': order.side.value,
                    'price': order.price,
                    'quantity': order.quantity,
                })
    obs['my_orders'] = my_orders
    return obs
```

注意：修改观测空间后需同步更新 `_build_spaces()` 中 `obs_space` 的定义，确保 Gymnasium spaces 与实际观测结构一致。

### 添加历史特征

如需要最近的成交历史（Last Trades）：

```python
# 在 TradingEnv.__init__ 中添加
self._trade_history: list[Trade] = []

# 在 _settle_trades 中追加
def _settle_trades(self, ...):
    for trade in trades:
        self._trade_history.append(trade)
        ...

# 在 observe 中返回最近 N 笔成交
def observe(self, agent):
    obs = {...}
    obs['recent_trades'] = self._trade_history[-10:]
    return obs
```

## 扩展动作空间

当前动作空间为 `spaces.Dict`：

```python
act_space = spaces.Dict({
    'asset_id': spaces.Discrete(n_pairs),
    'side': spaces.Discrete(3),
    'price': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float64),
    'quantity': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float64),
})
```

### 支持多笔订单

将动作空间改为每个交易对一个动作：

```python
act_space = spaces.Dict({
    pair.id: spaces.Dict({
        'side': spaces.Discrete(3),
        'price': spaces.Box(...),
        'quantity': spaces.Box(...),
    })
    for pair in self._pair_list
})
```

然后在 `step()` 中遍历所有交易对，依次处理每笔非 HOLD 订单。注意这会改变 AEC 语义（一个 step 可能产生多笔订单），需确保训练算法兼容。

### 支持撤单动作

增加 `cancel_order_id` 字段：

```python
act_space = spaces.Dict({
    'asset_id': spaces.Discrete(n_pairs),
    'side': spaces.Discrete(3),
    'price': spaces.Box(...),
    'quantity': spaces.Box(...),
    'cancel_order_id': spaces.Text(100),   # 要撤销的订单 ID，空字符串表示不撤单
})
```

在 `step()` 中先执行撤单，再执行新订单。

## 测试规范

### 源文件与测试文件一一对应

| 源文件 | 测试文件 |
|--------|----------|
| `tmo/core/order.py` | `tests/tmo/core/test_order.py` |
| `tmo/core/order_book.py` | `tests/tmo/core/test_order_book.py` |
| `tmo/core/matcher.py` | `tests/tmo/core/test_matcher.py` |
| `tmo/config/schema.py` | `tests/tmo/config/test_schema.py` |
| `tmo/env/trading_env.py` | `tests/tmo/env/test_trading_env.py` |

### 新增功能的测试要求

新增核心逻辑时，必须提供对应的 pytest 单元测试：

```python
def test_new_feature() -> None:
    """测试新功能的行为。"""
    # Arrange：准备环境
    env = TradingEnv(config)
    env.reset()

    # Act：执行操作
    result = env.some_new_method(...)

    # Assert：验证结果
    assert result == expected
```

### 运行测试

```bash
source .venv/bin/activate

# 运行全部测试
pytest -n auto --import-mode=importlib

# 带覆盖率
pytest -n auto --import-mode=importlib --cov --cov-report=term-missing

# 提交前检查
pre-commit run --all-files
```

### 资产守恒不变量

`tests/examples/test_random_agents.py` 中的 `test_asset_conservation_random_episode` 是一个重要的不变量测试：跑完一个随机 episode 后，断言所有资产（agent 持仓 + 交易所手续费累计）的总量与初始总量相等。修改结算逻辑或手续费计算时，必须确保该测试通过。
