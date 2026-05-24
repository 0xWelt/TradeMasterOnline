# TradeMasterOnline 交易环境设计方案（MVP）

## 1. 定位

基于 [PettingZoo](https://pettingzoo.farama.org/) AEC API 的最简多智能体交易仿真环境。

**仅包含**：
- 通过**配置文件**创建环境：交易对、初始价格、Agent 数量、各 Agent 初始持仓
- 固定数量同构智能体在**多资产**限价订单簿中交易（如 BTC/USDT、ETH/USDT）
- AEC 序贯交互语义
- **撮合引擎**：价格优先、时间优先，含自成交保护（STP）
- **资金冻结**：下单时按资产维度全局扣除未成交挂单占用（防止跨交易对重复质押）

**明确排除（后续扩展）**：

| 功能 | 说明 |
|---|---|
| 训练算法 | PPO、QMIX 等，本仓库仅提供环境 |
| 开户销户 | `possible_agents` 在 `reset()` 后固定不变 |
| 外部事件 | Chance Node（宏观新闻、流动性冲击） |
| 奖励系统 | MVP 阶段 `reward = 0`，自定义奖励由外部训练算法实现 |
| 并行环境 | `VectorizedTradingEnv` |
| 价格粒度对齐 | `tick_size` / `step_size` / `min_notional` filter 校验已实现 |

---

## 2. MARL 概念设计

以部分可观测随机博弈（POSG）的框架定义环境。

POSG 的标准七元组：

$$(\mathcal{N}, \mathcal{S}, \{\mathcal{A}_i\}, \mathcal{T}, \{R_i\}, \{\mathcal{O}_i\}, \gamma)$$

其中：
- $\mathcal{N} = \{0, 1, \dots, N-1\}$：智能体集合，$N$ 由配置文件确定
- $\mathcal{S}$：全局状态空间（完整订单簿 + 所有持仓）
- $\mathcal{A}_i$：智能体 $i$ 的动作空间
- $\mathcal{T}(s' \mid s, a_0, \dots, a_{N-1})$：状态转移函数（本环境为确定性转移，仅当前行动的智能体动作有效）
- $R_i: \mathcal{S} \times \mathcal{A}_i \to \mathbb{R}$：智能体 $i$ 的奖励函数
- $\mathcal{O}_i$：智能体 $i$ 的观测空间
- $\gamma \in [0, 1]$：折扣因子（本环境为即时奖励，$\gamma$ 由外部训练算法决定）

### 2.1 状态空间 $\mathcal{S}$（全局状态，环境内部维护）

$$s = \left( \{B_p\}_{p \in \text{Pairs}}, \{\pi_s\}_{s \in \text{Symbols}}, \{h_i\}_{i \in \mathcal{N}} \right)$$

- $B_p$：交易对 $p$ 的完整订单簿（所有档位的买卖队列，含订单粒度的时间戳和下单者）
- $\pi_s$：资产 $s$ 的当前价格。对于作为某个交易对 base 的资产（如 BTC/USDT 中的 BTC），其价格定义为该交易对**上一笔成交价**（以 quote asset 计价）。初始值由配置文件 `initial_price` 确定，每次撮合产生成交后按最新成交价更新。
- $h_i = \{h_{i,s}\}_{s \in \text{Symbols}}$：智能体 $i$ 的各资产持仓（现货，非负）

### 2.2 观测空间 $\mathcal{O}_i$（每个智能体的局部观测）

$$o_i = \left( \{B_p^{\text{snap}}\}_{p \in \text{Pairs}}, h_i \right)$$

- $B_p^{\text{snap}}$：交易对 $p$ 的订单簿快照（仅前 $n$ 档的聚合价格和数量，不含订单粒度信息，也不含下单者身份）
- $h_i$：智能体 $i$ 自己的持仓（对其他智能体的持仓不可见）

**不完全信息来源**：智能体看不到其他智能体的持仓，也看不到订单簿中单个订单的归属。

### 2.3 动作空间 $\mathcal{A}_i$

$$a_i = (p, \text{side}, \text{price}, \text{qty})$$

- $p \in \{0, 1, \dots, P-1\}$：交易对索引（离散）
- $\text{side} \in \{0, 1, 2\}$：0=不动作，1=买入（base），2=卖出（base）（离散）
- $\text{price} \in \mathbb{R}_{\ge 0}$：限价（连续）
- $\text{qty} \in \mathbb{R}_{\ge 0}$：数量（连续）

### 2.4 奖励函数 $R_i$

$$R_i(s, a_i) = 0$$

MVP 阶段奖励恒为 0。环境仅负责状态转移和撮合逻辑，奖励定义留给外部训练算法或用户自定义。后续可扩展为持仓市值变化、已实现盈亏、夏普比率等。

**实现方式**：`step()` 中设置 `self.rewards[agent] = 0.0`，但**不调用** `_accumulate_rewards()`。`last()` 继承自 AECEnv，返回 `_cumulative_rewards[agent]`，该值在 `reset()` 时初始化为 0 且运行期不再改变。

### 2.5 状态转移 $\mathcal{T}$

1. 解析智能体 $i$ 的动作 $a_i = (p, \text{side}, \text{price}, \text{qty})$
2. 若 $\text{side} = 0$，无状态变化
3. 否则，**下单前合法性检查**：按资产维度全局扣除该智能体所有未成交挂单的冻结占用，确认余额充足（参考 Binance `free` 余额检查，不预扣手续费）
4. 在交易对 $p$ 的订单簿中创建限价订单，执行撮合
5. 更新智能体 $i$ 及对手的持仓 $h_i$（扣除/增加 base 和 quote 资产；手续费按 **Binance received-asset 模式**从收到的资产中扣除）
6. 推进到下一个智能体

### 2.6 资金冻结与可下单余额（Binance 模型）

参考 Binance Spot 的 `free` / `locked` 余额模型：

- **`free`**：可用于新订单、提现的可用余额
- **`locked`**：被未成交订单冻结的余额
- 本环境用 `holdings` 统一表示总额，通过 `_can_place_order` 实时计算可用余额（`free = holdings - locked`）

现货交易中，**买单冻结 quote 资产，卖单冻结 base 资产**，两者互不冲突。因此：

- **允许同交易对双向挂单**：一个智能体可以同时持有某交易对的未成交买单和卖单（参考 Binance OCO / 独立限价单）。
- **自成交保护（STP）**：撮合时若 incoming order 与 resting order 属于同一智能体，**取消 resting order**（被动订单），继续撮合。参考 Binance / QFEX 的默认 STP 策略。
- **跨交易对资金共享**：同一 quote 资产（如 USDT）在所有交易对中共享一个资金池；同一 base 资产（如 BTC）在所有交易对中也共享一个资金池。`_can_place_order` 在检查时会遍历**所有交易对**的订单簿，按资产维度全局统计冻结占用：
  - BUY：冻结量 = 该智能体所有以同一 `quote` 资产的未成交买单的 `price * qty` 之和
  - SELL：冻结量 = 该智能体所有以同一 `base` 资产的未成交卖单的 `qty` 之和

---

## 3. 实现映射

将第 2 节的数学形式化映射到代码实现。

### 3.1 与 PettingZoo AEC 的对应

| POSG 概念 | PettingZoo AEC 实现 |
|---|---|
| 全局状态 $s$ | `TradingEnv` 内部维护的完整订单簿和持仓 |
| 观测 $\mathcal{O}_i(s)$ | `last()` 返回的 `obs`（LOB 快照 + 自身持仓） |
| 动作 $a_i$ | `step(action)` 接收的 `dict` |
| 奖励 $R_i$ | `last()` 返回的 `reward`（恒为 0） |
| 状态转移 $\mathcal{T}$ | `step()` 内部的撮合和持仓更新 |
| 序贯决策 | `agent_iter()` 逐个选择智能体 |

### 3.2 全局状态 $\mathcal{S}$ 的实现

数学：$s = \left( \{B_p\}, \{\pi_s\}, \{h_i\} \right)$

代码：

```python
# TradingEnv.__init__
self.books: dict[str, OrderBook]       # {B_p}
self.prices: dict[str, float]          # {π_s}，最新成交价
self.holdings: dict[str, dict[str, float]]   # {h_i}
self._pair_by_id: dict[str, Any]       # pair_id -> pair 映射，用于跨交易对资金检查
```

- `OrderBook` 维护每个交易对的完整买卖队列（`_bids`、`_asks`、`_orders` 索引）
- `prices` 显式保存各资产最新成交价，初始来自配置 `initial_price`
- `holdings` 保存每个智能体的各资产持仓（现货，非负，由 `_can_place_order` 保证）
- 固定智能体数量：`len(self.agents)` 在 `reset()` 时由配置确定，运行期不变

### 3.3 观测空间 $\mathcal{O}_i$ 的实现

数学：$o_i = \left( \{B_p^{\text{snap}}\}, h_i \right)$

代码：`observe(agent)` 返回的 `dict`：

```python
{
    "books": {
        "BTC/USDT": {
            "bids": ndarray(shape=(n_levels, 2)),   # 前 n_levels 档
            "asks": ndarray(shape=(n_levels, 2)),
        },
        ...
    },
    "holdings": {"BTC": 1.0, "ETH": 10.0, "USDT": 100000.0},
}
```

- `books` 为每个交易对返回聚合后的前 $n$ 档价格和数量（不含订单粒度信息）
- `holdings` 仅包含当前智能体自己的持仓（看不到其他智能体）
- 不完全信息：智能体看不到其他智能体持仓，也看不到订单簿中单个订单的归属

### 3.4 动作空间 $\mathcal{A}_i$ 的实现

数学：$a_i = (p, \text{side}, \text{price}, \text{qty})$

代码：`step(action)` 接收的 `dict`：

```python
{
    "asset_id": 0,      # 交易对索引（离散）
    "side": 1,          # 0=不动作, 1=买入(base), 2=卖出(base)（离散）
    "price": 50123.5,   # 限价（连续 float）
    "quantity": 0.05,   # 数量（连续 float）
}
```

- `side=0` 时不创建订单，无状态变化
- `side=1`（买入）：减少 `holdings[quote]`，增加 `holdings[base]`
- `side=2`（卖出）：减少 `holdings[base]`，增加 `holdings[quote]`
- 价格、数量为连续 float，但下单前需通过 filter 校验（`tick_size`、`step_size`、`min_notional`）

### 3.5 奖励函数 $R_i$ 的实现

数学：$R_i(s, a_i) = 0$

代码：`last()` 返回 `reward=0.0`

- MVP 阶段 `_cumulative_rewards` 在 `reset()` 时初始化为 0，运行期不再更新
- 环境仅负责状态转移和撮合逻辑
- 手续费仍从 `holdings` 中实际扣除（影响可交易余额），但不体现在 reward 中
- 价格追踪 `prices` 仍维护，供外部训练算法自定义奖励时使用

### 3.6 状态转移 $\mathcal{T}$ 的实现

数学：6 步状态转移流程

代码：`TradingEnv.step(action)` 方法内部：

```python
def step(self, action: dict | None) -> None:
    # 1. 解析动作
    pair = self._pair_list[action["asset_id"]]
    side = Side(action["side"])
    price = action["price"]
    qty = action["quantity"]

    if side is Side.HOLD:
        return

    # 2. Filter 校验（参考 Binance PRICE_FILTER / LOT_SIZE / MIN_NOTIONAL）
    if price % pair.tick_size != 0:
        return   # 价格不符合步长
    if qty % pair.step_size != 0:
        return   # 数量不符合步长
    if price * qty < pair.min_notional:
        return   # 名义价值过低

    # 3. 下单前合法性检查（全局资金冻结扣除，不预扣手续费）
    if not self._can_place_order(agent, pair, side, price, qty):
        return   # 余额不足，拒绝下单

    # 4. 创建限价订单（默认 GTC）
    order = Order(..., side, price, qty, time_in_force=TimeInForce.GTC)

    # 5. 撮合（OrderBook 内部调用 Matcher）
    trades = self.books[pair.id].place_order(order)

    # 6. 更新持仓和手续费（Binance received-asset 模式）
    self._settle_trades(agent, pair, trades, side)

    # 7. 推进到下一个智能体
    self._advance_agent()
```

- 序贯撮合：`agent_iter()` 按固定顺序逐个选择智能体，每次 `step()` 仅处理一笔订单
- 合法性检查：`_can_place_order()` 在**创建订单前**检查余额，按资产维度全局扣除所有未成交挂单的冻结占用（跨交易对），但**不预扣手续费**（手续费在成交时从 received asset 扣除，参考 Binance）
- 撮合后按最新成交价更新 `prices`

### 3.7 撮合引擎

`Matcher.match(order, book)` 实现**价格优先、时间优先**：

- BUY order：从最低 ask 价格开始匹配，要求 ask price ≤ order price
- SELL order：从最高 bid 价格开始匹配，要求 bid price ≥ order price
- 同一价格档内按 FIFO（先到先出）顺序匹配

**自成交保护（STP）—— 取消 resting order**：
- 若 resting order 与 incoming order 属于同一智能体，`Matcher` **取消该 resting order**（从订单簿索引和队列中移除），继续检查同一价格档的下一个订单
- 若整个价格档的所有 resting order 均为自订单，则该档被清空，移至下一档
- 参考 Binance / QFEX 默认 STP 策略：passive order is canceled
- `Trade` 模型在创建时验证 `buyer_id != seller_id`

### 3.8 手续费结算（Binance Received-Asset 模式）

参考 Binance 主流实现：手续费从**收到的资产**中扣除，不增加支付资产的开销。

| 角色 | 付出 | 收到（扣除手续费后） |
|------|------|---------------------|
| BUY Taker | `notional` in quote | `qty * (1 - taker_fee)` in base |
| BUY Maker | `notional` in quote | `qty * (1 - maker_fee)` in base |
| SELL Taker | `qty` in base | `notional * (1 - taker_fee)` in quote |
| SELL Maker | `qty` in base | `notional * (1 - maker_fee)` in quote |

- 总手续费 = `notional * (taker_fee + maker_fee)`，从系统中"销毁"
- `_can_place_order` 检查余额时**不预留手续费**，因为手续费在成交后才从 received asset 扣除
- 代码实现：`_settle_trades()` 按上表更新 `holdings`

### 3.9 AEC 环境类签名

```python
class TradingEnv(AECEnv):
    @classmethod
    def from_config(cls, path: str) -> "TradingEnv": ...
    def reset(self, seed=None, options=None) -> None: ...
    def step(self, action: dict | None) -> None: ...
    def last(self, observe=True, ...) -> tuple[obs, reward, ...]: ...
    def agent_iter(self, max_iter=2**63) -> Iterator[str]: ...
```

**终止条件**：
- `truncation`：达到 `max_steps`（配置指定）
- `termination`：智能体净资产 ≤ 0（可选，默认关闭）

---

## 4. 配置系统

### 4.1 配置格式（YAML）

```yaml
# config.yaml
exchange:
  assets:
    - symbol: "BTC"
    - symbol: "ETH"
    - symbol: "USDT"

  pairs:
    - id: "BTC/USDT"
      base: "BTC"
      quote: "USDT"
      initial_price: 50000.0
      tick_size: 1.0           # 价格步长（filter 校验）
      step_size: 0.0001        # 数量步长（filter 校验）
      min_notional: 10.0       # 最小名义价值（filter 校验）
      n_levels: 5
      default_stp_mode: "expire_maker"  # STP 策略
    - id: "ETH/USDT"
      base: "ETH"
      quote: "USDT"
      initial_price: 3000.0
      tick_size: 0.1
      step_size: 0.001
      min_notional: 10.0
      n_levels: 5
      default_stp_mode: "expire_maker"

  fees:
    maker_fee: 0.001
    taker_fee: 0.002
    # 可选：精度控制（MVP 外）
    # base_precision: 8
    # quote_precision: 8

agents:
  n_agents: 4
  initial_holdings:            # 支持两种格式
    - BTC: 2.0                 # 格式 A：list[dict]，每个 agent 一个 dict
      ETH: 5.0
      USDT: 80000.0
    - BTC: 1.0
      ETH: 10.0
      USDT: 100000.0
    # ...（长度必须等于 n_agents）
    # 格式 B：单个 dict，统一应用到所有 agent
    # BTC: 1.0
    # ETH: 10.0
    # USDT: 100000.0
  max_qty: 100

env:
  max_steps: 1000
  check_negative_equity: false
```

### 4.2 环境创建

```python
env = TradingEnv.from_config("config.yaml")
```

`from_config` 解析 YAML，按第 3 节描述初始化 `books`、`prices`、`holdings`。

---

## 5. 文件结构

源文件与测试文件一一对应：

```
tmo/
├── __init__.py
├── config/
│   ├── __init__.py
│   └── schema.py              # Pydantic 配置模型
├── core/
│   ├── __init__.py
│   ├── order.py               # Order, Trade, Side 枚举
│   ├── order_book.py          # OrderBook, PriceLevel
│   └── matcher.py             # Matcher（价格优先时间优先 + STP）
└── env/
    ├── __init__.py
    └── trading_env.py         # TradingEnv (AECEnv)

tests/tmo/                      # 与 tmo/ 目录结构镜像
├── config/
│   └── test_schema.py
├── core/
│   ├── test_order.py
│   ├── test_order_book.py
│   └── test_matcher.py
└── env/
    └── test_trading_env.py

examples/
├── configs/
│   └── default.yaml           # 默认配置示例（差异化持仓）
└── random_agents.py           # 随机智能体演示 + 结果绘图

docs/plan/
└── 2026-05-24_trading_env_mvp_design.md
```

---

## 6. 实现状态

### Step 1：核心引擎
- [x] `tmo/core/order.py`：`Order` + `Trade` Pydantic 模型，`Side` 枚举含 `HOLD=0`
- [x] `tmo/core/order_book.py`：`PriceLevel`（FIFO deque）+ `OrderBook`（bids/asks/orders 索引）
- [x] `tmo/core/matcher.py`：`Matcher.match()` 价格优先时间优先，**STP 取消 resting order**
- [x] 测试：`tests/tmo/core/test_order.py`、`test_order_book.py`、`test_matcher.py`

### Step 2：配置系统
- [x] `tmo/config/schema.py`：`ConfigSchema` Pydantic 模型，支持统一或差异化 `initial_holdings`
- [x] `examples/configs/default.yaml`：默认配置示例
- [x] 测试：`tests/tmo/config/test_schema.py`

### Step 3：AEC 环境
- [x] `tmo/env/trading_env.py`：`TradingEnv(AECEnv)`
  - [x] 全局资金冻结检查（跨交易对按资产维度扣除，`_can_place_order`）
  - [x] Filter 校验（`tick_size`, `step_size`, `min_notional`）
  - [x] 手续费 Binance received-asset 模式（从收到的资产中扣除）
  - [x] `exchange_holdings` 收集手续费，确保资产守恒
  - [x] 终止/截断条件
- [x] 测试：`tests/tmo/env/test_trading_env.py`（含资产守恒不变量）

### Step 4：订单模型扩展（调研 §6.1, §6.3）
- [x] `OrderStatus` 枚举：`NEW`, `PARTIALLY_FILLED`, `FILLED`, `CANCELED`, `EXPIRED`
- [x] `TimeInForce` 枚举：`GTC`, `IOC`, `FOK`（当前实现默认 GTC）
- [x] `Order` 模型扩展字段：`status`, `time_in_force`, `filled_qty`
- [ ] ~~STP 可配置化（`expire_maker` / `cancel_newest` / `cancel_both`）~~ — MVP 阶段固定 `expire_maker`

### Step 5：示例
- [x] `examples/random_agents.py`：随机动作跑通完整 episode
- [x] 绘制价格曲线（每交易对独立子图 + 独立 Y 轴）和 agent equity 曲线
- [x] 打印 episode 统计（成交数、各 agent 初始/最终 equity）
