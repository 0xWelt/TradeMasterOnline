# 主流数字货币交易所交易机制深度调研报告

> 调研目标：为 TradeMasterOnline 的交易仿真环境设计提供真实交易所的运行机制参考，深入理解撮合引擎、订单簿、自成交保护、资金冻结、手续费结算等核心概念的业界实现细节。
>
> 本报告基于 Binance、OKX、Bybit、Coinbase、Kraken 等主流交易所的官方 API 文档和交易规则，辅以 FIX 协议标准、ABIDES 等学术仿真框架的公开资料。所有引用均来自真实文档。

---

## 目录

- [1. 范围与方法](#1-范围与方法)
- [2. 核心概念](#2-核心概念)
  - [2.1 限价订单簿（LOB）](#21-限价订单簿lob)
  - [2.2 撮合引擎](#22-撮合引擎)
  - [2.3 自成交保护（STP）](#23-自成交保护stp)
  - [2.4 余额与资金冻结模型](#24-余额与资金冻结模型)
  - [2.5 手续费结算模式](#25-手续费结算模式)
  - [2.6 订单生命周期与 Time in Force](#26-订单生命周期与-time-in-force)
  - [2.7 价格与数量限制](#27-价格与数量限制)
- [3. 来源分析](#3-来源分析)
  - [3.1 Binance](#31-binance)
  - [3.2 OKX](#32-okx)
  - [3.3 Bybit](#33-bybit)
  - [3.4 Coinbase](#34-coinbase)
  - [3.5 Kraken & 传统交易所](#35-kraken--传统交易所)
- [4. 横向对比分析](#4-横向对比分析)
  - [4.1 核心机制对比矩阵](#41-核心机制对比矩阵)
  - [4.2 STP 策略对比](#42-stp-策略对比)
  - [4.3 余额模型对比](#43-余额模型对比)
  - [4.4 手续费对比](#44-手续费对比)
- [5. 领域发现：学术仿真与行业标准](#5-领域发现学术仿真与行业标准)
  - [5.1 ABIDES 等 Agent-Based 仿真框架](#51-abides-等-agent-based-仿真框架)
  - [5.2 FIX 协议中的 STP 标准](#52-fix-协议中的-stp-标准)
  - [5.3 传统交易所 vs 数字货币交易所](#53-传统交易所-vs-数字货币交易所)
- [6. 对 TradeMasterOnline 的设计建议](#6-对-trademasteronline-的设计建议)
- [7. 参考资料](#7-参考资料)
- [8. MVP 外常用功能前瞻](#8-mvp-外常用功能前瞻)
  - [8.1 市价委托](#81-市价委托)
  - [8.2 止盈止损与条件单](#82-止盈止损与条件单)
  - [8.3 OCO 订单](#83-oco-订单)
  - [8.4 跟踪止损](#84-跟踪止损)
  - [8.5 杠杆与保证金](#85-杠杆与保证金)
  - [8.6 永续合约](#86-永续合约)
  - [8.7 交割期货](#87-交割期货)
  - [8.8 期权](#88-期权)
  - [8.9 功能实现优先级建议](#89-功能实现优先级建议)

---

## 1. 范围与方法

### 调研范围

本次调研聚焦于**现货交易**的以下核心机制：

1. **撮合引擎（Matching Engine）**：价格优先、时间优先的具体实现，订单簿数据结构
2. **自成交保护（Self-Trade Prevention, STP）**：策略类型、默认行为、触发条件
3. **余额与资金冻结模型**：`free`/`locked` 定义、下单冻结逻辑、跨交易对资金共享
4. **手续费结算模式**：received-asset 扣除、Maker/Taker 区分、费率结构
5. **订单类型与生命周期**：LIMIT、MARKET、OCO 等，状态流转，Time in Force 策略
6. **价格与数量限制**：tick size、step size、min notional 等 filter 校验

**明确排除**：
- 合约/衍生品交易的保证金、强平、资金费率机制
- 链上结算与清算细节
- 交易所级别的风控（如反洗钱、KYC）

### 调研方法

1. **官方文档抓取**：直接抓取各交易所 GitHub/API 文档仓库中的 REST API 定义、FAQ、交易规则
2. **多源交叉验证**：对同一机制查阅多个交易所的文档，识别共性与差异
3. **学术文献补充**：查阅 ABIDES 等开源仿真框架论文，以及市场微观结构经典文献
4. **行业标准对照**：参考 FIX 协议（Tag 7928 SelfTradeType）中关于 STP 和撮合的标准定义

### 调研对象优先级

| 优先级 | 交易所 | 理由 |
|--------|--------|------|
| P0 | Binance | 交易量全球第一，plan 中已多次引用为参考 |
| P0 | OKX | 统一账户体系最具代表性，API 设计清晰 |
| P1 | Bybit | 衍生品起家，现货发展迅速，SMP 文档透明 |
| P1 | Coinbase | 美国最大合规交易所，费率结构与传统金融接近 |
| P2 | Kraken | 老牌交易所，FIX 协议支持好，STP 参数简洁 |
| P2 | Nasdaq / NYSE / Euronext | 传统交易所撮合规则，提供 STP 行业标准参照 |

---

## 2. 核心概念

### 2.1 限价订单簿（LOB）

限价订单簿（Limit Order Book, LOB）是中心化交易所的核心数据结构，维护所有未成交的限价买单（bids）和卖单（asks）。

**数学表示**：

$$B_p = (\text{Bids}_p, \text{Asks}_p)$$

其中：
- $\text{Bids}_p = \{(p_i, q_i, t_i, a_i)\}$：交易对 $p$ 的所有未成交买单，按价格降序排列
- $\text{Asks}_p = \{(p_j, q_j, t_j, a_j)\}$：交易对 $p$ 的所有未成交卖单，按价格升序排列
- 每个订单包含：价格 $p$、数量 $q$、时间戳 $t$、下单者 $a$

**关键属性**：
- **中间价（Mid Price）**：$\pi_p = (\text{best bid} + \text{best ask}) / 2$
- **买卖价差（Bid-Ask Spread）**：$\text{spread} = \text{best ask} - \text{best bid}$
- **深度（Depth）**：各价格档位的累积数量，反映市场流动性

**订单簿快照 vs 完整订单簿**：
- **完整订单簿**：包含每个订单的粒度信息（价格、数量、时间戳、下单者），仅供交易所内部使用
- **快照（Snapshot）**：仅返回前 $n$ 档的聚合价格和数量，通过公共 API 暴露给交易者

> Binance `GET /api/v3/depth` 返回：
> ```json
> {
>     "lastUpdateId": 1027024,
>     "bids": [["4.00000000", "431.00000000"]],
>     "asks": [["4.00000200", "12.00000000"]]
> }
> ```
> 每档为 `[价格, 累计数量]`，bids 降序、asks 升序。

### 2.2 撮合引擎

撮合引擎（Matching Engine）是交易所的核心交易执行系统，负责将 incoming order 与订单簿中的 resting order 进行匹配。

#### 价格优先、时间优先（Price-Time Priority）

这是绝大多数交易所采用的撮合规则：

1. **价格优先**：买单优先匹配最低 ask 价格，卖单优先匹配最高 bid 价格
2. **时间优先（FIFO）**：同一价格档内，先到达的订单先成交

**撮合流程**（以 incoming BUY limit order 为例）：

```
1. 从最低 ask 价格档开始遍历
2. 若 ask price <= order price，则匹配
3. 在该价格档内按 FIFO 顺序匹配 resting orders
4. 若 resting order 数量 < 剩余数量，消耗该 resting order，移至下一订单
5. 若 resting order 数量 >= 剩余数量，部分成交 resting order，incoming order 完全成交
6. 若 ask price > order price 或订单簿为空，停止匹配，剩余数量入簿
```

**成交价规则**：
- incoming 限价单/市价单 与 resting 限价单 成交时，**以 resting 订单的价格作为成交价**
- 这是行业通用规则，确保 resting order 获得其指定的价格

**Order Amend Keep Priority**：
- Binance 支持修改未成交订单的数量而不丢失时间优先权
- 这与传统的 cancel-replace（取消后重新排队）不同，后者会重置时间戳

### 2.3 自成交保护（STP）

自成交保护（Self-Trade Prevention, STP）是防止同一用户/账户的相反方向订单相互成交的机制。

#### 为什么需要 STP？

1. **防止洗量（Wash Trading）**：同一主体自买自卖制造虚假成交量
2. **防止意外对冲**：策略误操作导致同一账户的订单互为对手方
3. **合规要求**：多数监管辖区要求交易所具备 STP 能力

#### STP 策略类型（行业通用分类）

| 策略 | 行为描述 | 别名 |
|------|----------|------|
| Cancel Newest / Expire Taker | 取消 incoming（新）订单 | EXPIRE_TAKER |
| Cancel Oldest / Expire Maker | 取消 resting（老）订单 | EXPIRE_MAKER |
| Cancel Both | 两个订单均取消 | EXPIRE_BOTH |
| Decrement | 双方减量，较小订单 expire | DECREMENT |
| None | 允许自成交 | NONE |

#### STP 触发条件

1. 两个订单方向相反（Buy vs Sell）
2. 属于**同一识别实体**：同一账户、同一 MPID、同一 STP ID / Trade Group
3. 处于**连续交易阶段**（集合竞价阶段通常不触发 STP）

#### STP 与部分成交

若 incoming order 在匹配过程中遇到多个 resting orders：
- 先与不触发 STP 的订单部分成交
- 当遇到触发 STP 的订单时，按 STP 策略处理剩余量
- 若整个价格档的所有 resting order 均触发 STP，则该档被清空，移至下一档

### 2.4 余额与资金冻结模型

#### 经典模型：free / locked 分离

| 字段 | 含义 |
|------|------|
| `free` | 可用余额，可用于新订单、提现 |
| `locked` | 被未成交订单冻结的余额 |
| **总额** | `free + locked` |

**冻结逻辑**：
- **BUY 订单**：冻结 `price * quantity` 的 **quote 资产**
- **SELL 订单**：冻结 `quantity` 的 **base 资产**

**跨交易对资金共享**：
- 同一 quote 资产（如 USDT）在所有交易对中共享一个资金池
- 同一 base 资产（如 BTC）在所有交易对中也共享一个资金池
- 某交易对的买单会扣减该 quote 资产在所有交易对中的可用余额

**成交后的资金转移**：
- BUY 成交：quote 资产从 locked 扣除，base 资产增加到 free（扣除手续费后）
- SELL 成交：base 资产从 locked 扣除，quote 资产增加到 free（扣除手续费后）

#### 高级模型：统一账户（Unified Account）

OKX、Bybit 等交易所推出的统一账户模型：

| 字段 | 含义 |
|------|------|
| `walletBalance` | 钱包余额（入金 + 已实现盈亏） |
| `equity` | 资产权益 = walletBalance − borrow + unrealized PnL |
| `availBal` / `availableToTrade` | 可用余额（可下单/转出的资金） |
| `frozenBal` / `locked` / `ordFrozen` | 被挂单冻结的余额 |
| `imr` | 初始保证金要求 |
| `mmr` | 维持保证金要求 |

统一账户的核心优势是**跨币种、跨产品共享保证金**，所有币种按汇率折算为 USD 计算可用保证金。

### 2.5 手续费结算模式

#### Maker-Taker 模型

- **Maker（做市商）**：提交限价单并进入订单簿等待成交的订单，提供流动性
- **Taker（吃单者）**：与订单簿中已有订单立即成交的订单，消耗流动性
- 通常 **Taker 费率 > Maker 费率**，以激励流动性提供

#### Received-Asset 手续费扣除

主流交易所（Binance、OKX、Bybit 等）采用此模式：

| 角色 | 付出资产 | 收到资产（扣除手续费后） |
|------|----------|------------------------|
| BUY Taker | `notional = price * qty` in quote | `qty * (1 - taker_fee)` in base |
| BUY Maker | `notional = price * qty` in quote | `qty * (1 - maker_fee)` in base |
| SELL Taker | `qty` in base | `notional * (1 - taker_fee)` in quote |
| SELL Maker | `qty` in base | `notional * (1 - maker_fee)` in quote |

**关键特性**：
- 手续费从**收到的资产**中扣除
- 不增加支付资产的开销
- 总手续费 = `notional * (taker_fee + maker_fee)`，从系统中"销毁"

**余额检查时不预扣手续费**：因为手续费在成交后才从 received asset 扣除，所以下单时只需检查 `free >= required`，不需要额外预留手续费金额。

### 2.6 订单生命周期与 Time in Force

#### 订单状态流转

```
NEW → PARTIALLY_FILLED → FILLED
 ↓
CANCELED (by user)
 ↓
EXPIRED (by TIF rules or STP)
 ↓
REJECTED (insufficient balance or filter failure)
```

| 状态 | 说明 |
|------|------|
| `NEW` | 订单已被引擎接受 |
| `PARTIALLY_FILLED` | 部分成交 |
| `FILLED` | 完全成交 |
| `CANCELED` | 用户取消 |
| `EXPIRED` | 按规则过期（IOC/FOK 未成交部分、STP 触发） |
| `REJECTED` | 被引擎拒绝 |

#### Time in Force（TIF）策略

| 策略 | 缩写 | 行为 |
|------|------|------|
| Good Till Canceled | GTC | 一直有效直到取消或完全成交 |
| Immediate Or Cancel | IOC | 立即成交可成交部分，剩余取消 |
| Fill Or Kill | FOK | 必须完全成交，否则全部取消 |
| Post Only | — | 仅作为 maker 挂单，若会立即成交则拒绝 |

### 2.7 价格与数量限制

交易所通过 filter 机制限制下单的价格和数量，以维护市场秩序。

| Filter | 字段 | 说明 | Binance 名称 |
|--------|------|------|-------------|
| 价格步长 | `tickSize` / `tickSz` | 价格必须是此值的整数倍 | PRICE_FILTER |
| 数量步长 | `stepSize` / `lotSz` / `qtyStep` | 数量必须是此值的整数倍 | LOT_SIZE |
| 最小名义价值 | `minNotional` / `minSz` | `price * quantity >= minNotional` | MIN_NOTIONAL |
| 价格范围 | `minPrice` / `maxPrice` | 价格必须在范围内 | PRICE_FILTER |
| 数量范围 | `minQty` / `maxQty` | 数量必须在范围内 | LOT_SIZE |

**验证规则**：
- `price % tickSize == 0`
- `quantity % stepSize == 0`
- `price * quantity >= minNotional`
- `minPrice <= price <= maxPrice`
- `minQty <= quantity <= maxQty`

---

## 3. 来源分析

### 3.1 Binance

**资源**：
- [Binance Spot REST API 文档](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md)
- [Binance STP FAQ](https://github.com/binance/binance-spot-api-docs/blob/master/faqs/stp_faq.md)
- [Binance API ENUM 定义](https://github.com/binance/binance-spot-api-docs/blob/master/enums.md)
- [Binance Order Amend Keep Priority](https://github.com/binance/binance-spot-api-docs/blob/master/faqs/order_amend_keep_priority.md)

**核心发现**：

#### 撮合引擎
- 严格遵循**价格优先、时间优先**原则
- 支持 **Order Amend Keep Priority**：修改数量不丢失时间优先权
- `GET /api/v3/depth` 返回 bids 降序、asks 升序，每档为 `[价格, 累计数量]`

#### STP
- 支持 **6 种 STP 模式**：`NONE`、`EXPIRE_TAKER`、`EXPIRE_MAKER`、`EXPIRE_BOTH`、`DECREMENT`、`TRANSFER`
- **默认策略由交易对配置决定**，通过 `GET /api/v3/exchangeInfo` 查询 `defaultSelfTradePreventionMode`
- 注意：不同来源文档对"默认策略"描述不一致，部分第三方文档称默认是 `EXPIRE_MAKER`，但官方 API 返回应以 `exchangeInfo` 为准
- 因 STP 过期的订单状态为 **`EXPIRED_IN_MATCH`**
- 支持 `tradeGroupId` 实现跨账户 STP

#### 余额模型
- `GET /api/v3/account` 返回 `balances` 数组，每个元素含 `asset`、`free`、`locked`
- 买单冻结 quote，卖单冻结 base
- 同一 quote 资产在所有交易对中共享资金池

#### 手续费
- 现货默认：Maker 0.1%，Taker 0.1%
- `GET /api/v3/account` 返回 `makerCommission` 和 `takerCommission`（单位为 0.01%）
- BNB 抵扣可享 25% 折扣
- `fills` 数组中返回每笔成交的 `commission` 和 `commissionAsset`

#### 订单类型
- 支持 `LIMIT`、`LIMIT_MAKER`、`MARKET`、`STOP_LOSS`、`STOP_LOSS_LIMIT`、`TAKE_PROFIT`、`TAKE_PROFIT_LIMIT`
- OCO 订单：限价单 + 止损限价单绑定，一个成交后另一个自动取消

#### 价格/数量限制
- `GET /api/v3/exchangeInfo` 的 `filters` 数组定义各交易对限制
- `PRICE_FILTER`：`minPrice`、`maxPrice`、`tickSize`
- `LOT_SIZE`：`minQty`、`maxQty`、`stepSize`
- `MIN_NOTIONAL` / `NOTIONAL`：`minNotional`、`maxNotional`
- `MAX_POSITION`：最大持仓限制

### 3.2 OKX

**资源**：
- [OKX V5 API 官方文档](https://www.okx.com/docs-v5/en/)
- [OKX 统一账户解读](https://www.odaily.news/post/5192009)

**核心发现**：

#### 撮合引擎
- 价格优先 + 时间优先
- 单 taker 订单最多匹配 **1000 个** maker 订单，超出部分取消
- 每交易对最大挂单笔数：**500 笔**
- 全账户级别最大挂单笔数：**4,000 笔**

#### STP
- 通过 `stpId` + `stpMode` 配置
- `stpMode`：`cancel_maker`、`cancel_taker`、`cancel_both`
- 同一用户（含主账户和子账户）之间的订单匹配视为自成交
- STP 在 FOK 订单中**不生效**

#### 余额模型
- 四种账户模式：Spot mode、Futures mode、Multi-currency margin、Portfolio margin
- 核心字段：`cashBal`（现金）、`eq`（权益）、`availBal`（可用）、`frozenBal`（冻结）、`ordFrozen`（订单冻结）
- 统一账户下，所有币种按 USD 折算共享保证金
- 支持**自动借币**：余额不足时自动借入

#### 手续费
- 现货：Maker 0.08%，Taker 0.10%
- 合约：Maker 0.02%，Taker 0.05%
- VIP 7+ maker 费率为**负值**（交易所返佣）
- OKB 折扣最高 40%

#### 订单类型
- 支持 `market`、`limit`、`post_only`、`fok`、`ioc`、`conditional`、`oco`、`move_order_stop`（跟踪止损）、`iceberg`、`twap`
- `limit` 默认等效于 GTC

#### 价格/数量限制
- `GET /api/v5/account/instruments` 返回 `tickSz`、`lotSz`、`minSz`、`maxLmtSz`、`maxMktSz`
- 新上币 10 分钟后启用**限价价格保护规则**

### 3.3 Bybit

**资源**：
- [Bybit V5 API 文档（下单）](https://bybit-exchange.github.io/docs/v5/order/create-order)
- [Bybit V5 SMP 文档](https://bybit-exchange.github.io/docs/v5/smp)
- [Bybit V5 钱包余额](https://bybit-exchange.github.io/docs/v5/account/wallet-balance)
- [Bybit V5 手续费率](https://bybit-exchange.github.io/docs/v5/account/fee-rate)

**核心发现**：

#### 撮合引擎
- 价格-时间优先（FIFO），内存订单簿
- 单个合约支持高达 **100,000 TPS**
- Snapshot + Delta 的 WebSocket 数据分发模式

#### STP（SMP）
- 功能名称：Self Match Prevention（SMP）
- 三种策略：`CancelMaker`、`CancelTaker`、`CancelBoth`
- 通过 `smpType` 参数在**下单时**指定
- 支持 **SMP Trade Group**：将多个 UID 编组，组内 UID 之间也受 SMP 保护

#### 余额模型
- **Unified Trading Account（UTA）** 统一交易账户
- 核心字段：`walletBalance`、`locked`、`equity`、`totalOrderIM`、`totalPositionIM`、`totalAvailableBalance`
- 现货卖出冻结持仓，买入冻结计价货币

#### 手续费
- 现货：Maker 0.10%，Taker 0.10%
- USDT 永续：Maker 0.02%，Taker 0.055%
- `Transaction Log` 中 `fee` 为正表示支出，为负表示返佣

#### 订单类型
- 基础：`Limit`、`Market`
- TIF：`GTC`、`IOC`、`FOK`、`PostOnly`
- 高级：Conditional、TP/SL、OCO（Spot）、`reduceOnly`、`closeOnTrigger`
- 支持修改未成交或部分成交订单

#### 价格/数量限制
- `Get Instruments Info` 返回 `priceFilter` + `lotSizeFilter` + `riskParameters`
- `minNotionalValue`、`priceLimitRatioX` / `priceLimitRatioY`（价格涨跌幅限制）

### 3.4 Coinbase

**资源**：
- [Coinbase Advanced Trade API](https://coinbase-cloud.mintlify.app/coinbase-app/advanced-trade-apis/rest-api)
- [Coinbase Developer Docs 索引](https://docs.cloud.coinbase.com/llms.txt)

**核心发现**：

#### 撮合引擎
- 经典的**价格-时间优先**中心化限价订单簿（CLOB）
- 撮合延迟在**个位数微秒**，每秒处理 100,000+ 订单
- Public API 有 1 秒缓存，推荐用 WebSocket 获取实时数据

#### STP
- 公开 API 文档中**未明确披露 STP 的具体策略配置**
- 从行业实践推断，Coinbase 在撮合层有内部自成交保护机制
- 机构级（Coinbase Prime）可能支持更精细的 STP 配置

#### 余额模型
- **分币种账户（Account-per-Currency）** 模型
- 核心字段：`available_balance`、`hold`
- 支持 **Portfolio** 功能：创建多个子组合，资金可在 Portfolio 之间划转
- 衍生品（FCM 期货）有独立的 `balance_summary` 和 `sweep` 机制

#### 手续费
- Advanced Trade 基础费率：**Maker 0.40%~0.60%，Taker 0.60%~1.20%**（显著高于 Binance/OKX/Bybit）
- 稳定币对：Maker 0.00%，Taker 0.10%~0.45%
- 最高层级（月交易量 $250M+）：Maker 0.00%，Taker 0.05%

#### 订单类型
- 使用强类型的 **order configuration** 对象：
  - `market_market_ioc`（现货市价单）
  - `limit_limit_gtc` / `limit_limit_gtd` / `limit_limit_fok`
  - `stop_limit_stop_limit_gtc` / `stop_limit_stop_limit_gtd`
  - `trigger_bracket_order_gtc` / `trigger_bracket_order_gtd`
- 支持 `post_only`、`reduce_only` 执行指令
- 支持 `preview_order` 在下单前模拟执行结果

#### 价格/数量限制
- `Get Product` 返回 `base_increment`（数量精度）、`quote_increment`（价格精度）、`base_min_size` / `base_max_size`

### 3.5 Kraken & 传统交易所

**资源**：
- [Kraken REST API (Add Order)](https://docs.kraken.com/api/docs/rest-api/add-order)
- [Nasdaq STP Factsheet](https://www.nasdaq.com/docs/2024/04/02/Self-Trade-Prevention_Factsheet.pdf)
- [NYSE Pillar FIX Protocol Specification](https://www.nyse.com/publicdocs/nyse/NYSE_Pillar_Gateway_FIX_Protocol_Specification.pdf)
- [Euronext Optiq STP Functional Overview v2.0](https://connect2.euronext.com/sites/default/files/it-documentation/Self-Trade%20Prevention%20Functional%20Overview%20-%20v2.0.pdf)

**核心发现**：

#### Kraken
- STP 参数：`stptype` = `cancel-newest`（默认）/ `cancel-oldest` / `cancel-both`
- 支持 `deadline`（RFC3339 时间戳 + 60 秒内）：定义撮合引擎必须拒绝订单的时间点
- 支持条件平仓单（conditional close orders）

#### Nasdaq
- STP 默认策略：**Cancel Passive（等效于 Cancel Oldest / Expire Maker）**
- 支持三种粒度：MPID+Trader ID / MPID / Specified Trader Group
- 支持 **Create Technical Transfer**：将自成交转换为内部划转（类似 Binance 的 TRANSFER）

#### NYSE Pillar
- FIX Tag 7928：`T`（None）、`N`（Cancel Newest）、`O`（Cancel Oldest）、`C`（Cancel Both）、`D`（Decrement）
- 支持 MPID-based 或 ClientID-based STP
- 支持 Session 级默认配置

#### Euronext Optiq
- `Cancel Resting` / `Cancel Incoming` / `Cancel Both`
- 仅适用于连续交易阶段
- 支持 IMS（Internal Matching Service）兼容

---

## 4. 横向对比分析

### 4.1 核心机制对比矩阵

| 维度 | Binance | OKX | Bybit | Coinbase | Kraken |
|------|---------|-----|-------|----------|--------|
| **撮合算法** | Price-Time Priority | Price-Time Priority | Price-Time Priority | Price-Time Priority | Price-Time Priority |
| **内存订单簿** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **单对最大挂单** | 未公开 | 500 | 未公开 | 未公开 | 未公开 |
| **全账户最大挂单** | 未公开 | 4,000 | 未公开 | 未公开 | 未公开 |
| **单 taker 最大匹配数** | 未公开 | 1,000 maker | 未公开 | 未公开 | 未公开 |
| **Order Amend Keep Priority** | ✅ | ❓ | ❓ | ❓ | ❓ |
| **市价单** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **限价单** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **OCO 订单** | ✅ | ✅ | ✅（Spot） | ✅（Bracket） | ✅ |
| **止损/止盈** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **冰山订单** | ❌ | ✅ | ❌ | ❌ | ❌ |
| **TWAP/VWAP** | ❌ | ✅（TWAP） | ❌ | ✅ | ❌ |
| **预览下单** | ❌ | ❌ | ❌ | ✅ | ❌ |

### 4.2 STP 策略对比

| 交易所 | 策略名称 | 策略数量 | 默认策略 | 订单级配置 | 跨账户/组支持 |
|--------|----------|----------|----------|------------|---------------|
| **Binance** | EXPIRE_TAKER / EXPIRE_MAKER / EXPIRE_BOTH / DECREMENT / TRANSFER / NONE | 6 | 交易对配置（可能为 NONE） | ✅ `selfTradePreventionMode` | ✅ `tradeGroupId` |
| **OKX** | cancel_taker / cancel_maker / cancel_both | 3 | 未明确（内部逻辑） | ✅ `stpId` + `stpMode` | ✅（主子账户间） |
| **Bybit** | CancelMaker / CancelTaker / CancelBoth | 3 | 未明确 | ✅ `smpType` | ✅ SMP Trade Group |
| **Coinbase** | 内部机制 | — | Cancel-Newest（推断） | ❌（未公开） | ❓ |
| **Kraken** | cancel-newest / cancel-oldest / cancel-both | 3 | cancel-newest | ✅ `stptype` | ❌ |
| **Nasdaq** | Cancel Passive / Cancel Aggressive / Cancel Both / Technical Transfer | 4 | Cancel Passive | ✅ | ✅ MPID/Trader Group |
| **NYSE Pillar** | T/N/O/C/D (FIX Tag 7928) | 5 | 可配置 | ✅ | ✅ MPID/ClientID |
| **Euronext** | Cancel Resting / Cancel Incoming / Cancel Both | 3 | 可配置 | ✅ | ❌ |

### 4.3 余额模型对比

| 维度 | Binance | OKX | Bybit | Coinbase |
|------|---------|-----|-------|----------|
| **账户模型** | 经典分离 / 统一账户（UA） | 统一交易账户（UTA） | 统一交易账户（UTA） | 分币种账户 + Portfolio |
| **可用余额字段** | `free` | `availBal` | `totalAvailableBalance` | `available_balance` |
| **冻结余额字段** | `locked` | `frozenBal` / `ordFrozen` | `locked` | `hold` |
| **权益字段** | `crossWalletBalance` | `eq` / `adjEq` | `equity` | — |
| **跨币种保证金** | ✅（统一账户） | ✅（多币种保证金模式） | ✅ | ❌ |
| **自动借币** | ❓ | ✅ | ❓ | ❌ |
| **保证金比率** | `marginRatio` | `mgnRatio` | — | — |

### 4.4 手续费对比（现货基础费率）

| 交易所 | Maker | Taker | 折扣机制 |
|--------|-------|-------|----------|
| **Binance** | 0.10% | 0.10% | BNB 抵扣 25% |
| **OKX** | 0.08% | 0.10% | OKB 折扣最高 40%，VIP7+ maker 负费率 |
| **Bybit** | 0.10% | 0.10% | — |
| **Coinbase** | 0.40%~0.60% | 0.60%~1.20% | 交易量阶梯递减 |
| **Kraken** | 0.16% | 0.26% | 交易量阶梯递减 |

> 注：Coinbase 费率显著高于其他交易所（约 4~6 倍），因其主打合规和美国零售市场。

---

## 5. 领域发现：学术仿真与行业标准

### 5.1 ABIDES 等 Agent-Based 仿真框架

**ABIDES**（Byrd, Hybinette & Balch, 2019）是当前最突出的开源高保真股票市场仿真器：

- **离散事件仿真（Discrete Event Simulation）**：时间分辨率达到**纳秒级**
- **消息协议**：参照 NASDAQ 的 **ITCH/OUCH** 协议设计
- **网络延迟模拟**：可配置 Agent 之间、Agent 与交易所之间的成对延迟
- **Background Agent**：通过"数据神谕"获取带噪声的历史交易观测，混合先验信念形成后验价值信念，从而复现特定历史交易日的价格走势
- **ABIDES-MARL**（2025）：解耦内核中断与状态收集，支持同步多智能体强化学习

**Zero-Intelligence (ZI) 交易者模型**（Gode & Sunder, 1993）：
- 即使交易者完全没有智能（随机出价），只要受到预算约束，市场配置效率也能接近 100%
- **启示**：市场微观结构（制度设计）本身对市场效率和价格发现起主导作用，这为 LOB 仿真提供了最简基线

**Hawkes 过程模型**：
- 用于建模限价单、市价单和撤单到达时间的**相互激励**特性
- 市价单执行后，限价单更可能快速到达以"补充"被消耗的流动性
- 能够复现波动率聚集（volatility clustering）等关键微观结构特征

### 5.2 FIX 协议中的 STP 标准

FIX 协议是金融信息交换的国际标准，对 STP 有明确定义：

- **Tag 7928: SelfTradeType**（NYSE Pillar 采用）
  - `T` = No Self Trade Prevention
  - `N` = Cancel Newest
  - `O` = Cancel Oldest
  - `C` = Cancel Both
  - `D` = Cancel Decrement
- **Tag 2362: SelfMatchPreventionID**：可选的 STP ID，用于分组隔离

> 行业趋势：Cancel Oldest（即 Expire Maker / Cancel Passive）是最常见的默认策略，因为 resting order 已"承诺"提供流动性，incoming order 是"新"的。

### 5.3 传统交易所 vs 数字货币交易所

| 维度 | 传统交易所（Nasdaq/NYSE） | 数字货币交易所 |
|------|--------------------------|---------------|
| **交易时间** | 固定时段（如 9:30-16:00 ET），有开盘/收盘集合竞价 | 7×24 小时连续交易 |
| **撮合算法** | 以 Price-Time Priority 为主；部分期权支持 Pro-Rata（按比例分配） | 绝大多数采用 Price-Time Priority |
| **延迟要求** | 纳秒级竞争，共置（co-location）是重要优势 | 毫秒级已足够优秀 |
| **订单类型** | Market, Limit, Stop, IOC, FOK, GTC, Iceberg, ALO | 更丰富：Post-Only, Reduce-Only, OCO, Trailing Stop, 杠杆订单 |
| **STP 默认行为** | 通常默认启用或需显式配置 | 多数默认启用 STP |
| **最小价格单位** | 严格监管定义，按资产价格分级 | 由交易所自行设定，通常较小 |
| **结算与清算** | T+2 / T+1 集中清算（DTCC 等） | 实时或准实时结算 |
| **监管与合规** | 严格（SEC, FINRA, MiFID II）；有熔断机制、涨跌停限制 | 相对宽松；部分有价格保护机制 |
| **流动性结构** | 做市商义务、DMM（指定做市商）、Retail Priority 等复杂层级 | 主要靠用户自发流动性 + maker-taker 费率激励 |
| **市场数据协议** | ITCH, OUCH, FIX 5.0, SBE | REST/WebSocket API, 部分支持 FIX |

---

## 6. 对 TradeMasterOnline 的设计建议

基于以上调研，针对当前 `docs/plan/2026-05-24_trading_env_mvp_design.md` 中的设计，提出以下具体建议：

### 6.1 STP 默认策略可配置化

**现状**：当前设计固定为"取消 resting order"（等效于 `EXPIRE_MAKER` / `CancelMaker`），设计文档参考的"Binance / QFEX 默认 STP 策略"可能存在误读。

**问题**：
- Binance 官方 API 显示 `defaultSelfTradePreventionMode` 可能为 `"NONE"`（由交易对配置决定）
- 不同交易所默认策略不同：Kraken 默认 `cancel-newest`，Nasdaq 默认 `Cancel Passive`

**建议**：
- 在 `config.yaml` 中增加 `default_stp_mode` 字段，支持 `"expire_maker"`（默认）、`"expire_taker"`、`"expire_both"`、`"none"`
- 在 `Order` 模型中增加可选的 `stp_mode` 字段，允许单笔订单覆盖默认策略
- 在 `Matcher.match()` 的撮合循环中，按 STP 策略处理自成交，而非简单跳过
- 后续可考虑增加 `max_position` 限制（Binance 有此 filter）

### 6.2 手续费精度处理

**现状**：手续费按 `qty * (1 - fee)` 计算，可能存在浮点误差累积。

**建议**：
- 参考 Binance 的 `baseCommissionPrecision` 和 `quoteCommissionPrecision`，在 `_settle_trades()` 中对手续费金额进行精度截断
- 在 `config.yaml` 的 `fees` 下增加 `base_precision`、`quote_precision` 字段（或使用 Python `decimal.Decimal`）

### 6.3 订单状态流转图

建议明确以下状态流转：

```
NEW → PARTIALLY_FILLED → FILLED
 ↓
CANCELED (by user / by OCO trigger)
 ↓
EXPIRED (IOC/FOK rules, or STP triggered)
 ↓
REJECTED (filter failure, insufficient balance)
```

### 6.4 建议的 config.yaml 扩展

```yaml
exchange:
  pairs:
    - id: "BTC/USDT"
      base: "BTC"
      quote: "USDT"
      initial_price: 50000.0
      tick_size: 1.0          # 价格步长
      step_size: 0.0001       # 数量步长
      min_notional: 10.0      # 最小名义价值
      n_levels: 5
      default_stp_mode: "expire_maker"  # none / expire_maker / expire_taker / expire_both

  fees:
    maker_fee: 0.001
    taker_fee: 0.002
    # 可选：精度控制
    # base_precision: 8
    # quote_precision: 8
```

### 6.5 长期扩展方向

1. **引入 Zero-Intelligence 交易者**：作为最简基线，验证市场微观结构设计的正确性
2. **A/B 测试支持**：通过固定 PRNG 种子，确保实验可重复
3. **订单簿日志**：记录完整订单流，支持 price impact 分析
4. **延迟模型**：引入网络延迟和计算延迟，让滑点自然涌现
5. **更多订单类型**：MARKET、OCO、IOC、FOK、Post-Only
6. **历史数据回放**：参考 ABIDES 的 Background Agent 机制

---

## 7. 参考资料

### 交易所官方文档

1. Binance Spot REST API Docs: https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md
2. Binance STP FAQ: https://github.com/binance/binance-spot-api-docs/blob/master/faqs/stp_faq.md
3. Binance ENUM Definitions: https://github.com/binance/binance-spot-api-docs/blob/master/enums.md
4. OKX V5 API Docs: https://www.okx.com/docs-v5/en/
5. Bybit V5 API Docs: https://bybit-exchange.github.io/docs/v5/order/create-order
6. Bybit V5 SMP Docs: https://bybit-exchange.github.io/docs/v5/smp
7. Coinbase Advanced Trade API: https://coinbase-cloud.mintlify.app/coinbase-app/advanced-trade-apis/rest-api
8. Kraken REST API Docs: https://docs.kraken.com/api/docs/rest-api/add-order

### 传统交易所文档

9. Nasdaq STP Factsheet: https://www.nasdaq.com/docs/2024/04/02/Self-Trade-Prevention_Factsheet.pdf
10. NYSE Pillar FIX Protocol Specification: https://www.nyse.com/publicdocs/nyse/NYSE_Pillar_Gateway_FIX_Protocol_Specification.pdf
11. Euronext Optiq STP Functional Overview v2.0: https://connect2.euronext.com/sites/default/files/it-documentation/Self-Trade%20Prevention%20Functional%20Overview%20-%20v2.0.pdf
12. Nasdaq Equity Trading Rules: https://listingcenter.nasdaq.com/rulebook/nasdaq/rules/Nasdaq%20Equity%204

### 学术文献

13. ABIDES: Towards High-Fidelity Market Simulation for AI Research (arXiv:1904.12066): https://ar5iv.labs.arxiv.org/html/1904.12066
14. ABIDES-MARL: Multi-Agent RL for LOB Simulation (arXiv:2511.02016): https://arxiv.org/abs/2511.02016
15. ABIDES-Gym / RL Execution in ABIDES (arXiv:2006.05574): https://arxiv.org/abs/2006.05574
16. Limit Order Book Simulations: A Review (arXiv:2402.17359): https://arxiv.org/html/2402.17359v1
17. MAXE: Fast Agent-Based LOB Simulation (arXiv:2008.07871): https://arxiv.org/abs/2008.07871
18. Gode & Sunder (1993) Zero-Intelligence Traders, JPE 101(1):119-137
19. Kyle (1985) Continuous Auctions and Insider Trading, Econometrica 53:1315-1335
20. Cont, Stoikov & Talreja (2010) Stochastic Model for Order Book Dynamics, Operations Research 58(3)

### 开源项目

21. ABIDES GitHub: https://github.com/abides-sim/abides


---

## 8. MVP 外常用功能前瞻

本章节调研 MVP plan 中尚未涉及、但在真实交易所中广泛使用的交易功能，为后续扩展提供参考。

### 8.1 市价委托

#### 执行机制

市价单（Market Order）的核心逻辑是**立即以当前市场上最优可得价格成交**。当用户提交市价单后，交易所匹配引擎会将其与订单簿中对手方的最优挂单进行撮合：

- **买方向**：从订单簿的最低 ask 价格开始，逐层向上吃单，直到订单全部成交或订单簿该方向深度耗尽
- **卖方向**：从订单簿的最高 bid 价格开始，逐层向下吃单

**是否保证成交？** 市价单**不保证成交价格**，但通常保证成交（在订单簿有深度的情况下）。若订单簿对手方深度不足，市价单可能只部分成交，剩余部分通常按 **IOC（Immediate Or Cancel）** 逻辑处理——未成交部分立即取消，不会作为挂单留在簿册中。

#### 滑点（Slippage）

滑点是指订单期望成交价格与实际成交平均价格之间的偏差。产生原因：

1. **订单簿深度不足**：大额市价单会"穿透"多个价格层级，导致部分成交量在更差的价格上成交
2. **高波动性**：从下单到撮合的极短时间内，市场价格发生跳动
3. **网络延迟**：在极端行情下，订单到达服务器时最优价已发生变化

#### 按 Quote 金额下单 vs 按 Base 数量下单

| 交易所 | 现货市价买入 | 现货市价卖出 | 说明 |
|--------|-------------|-------------|------|
| **Binance** | `quoteOrderQty`（如 100 USDT） | `quantity`（如 0.01 BTC） | 买入按 quote 金额，卖出按 base 数量 |
| **OKX** | `sz`（buy 时隐式为 quote 金额） | `sz`（base 数量） | 方向隐式区分语义 |
| **Bybit** | `qty`（buy 时为 quote 金额） | `qty`（base 数量） | 与 Binance 类似 |

#### 市价单的 Taker 角色

市价单**几乎总是 Taker**，因为它立即与订单簿上现有的 Maker 订单撮合，吃掉了流动性。因此市价单通常适用较高的 **Taker Fee**。

#### 价格保护机制

交易所为防止市价单在极端行情下以离谱价格成交，设置了多层保护：

| 机制 | Binance | OKX | Bybit |
|------|---------|-----|-------|
| **Price Protect** | 期货支持 `priceProtect=true` | 通过限价逻辑实现 | 通过 `tpLimitPrice`/`slLimitPrice` 限制 |
| **数量限制** | `MARKET_LOT_SIZE` / `NOTIONAL` | `maxMktSz` / `maxMktAmt` | `maxMktOrderQty` |

#### 对仿真环境的启示

- 市价单仿真实现难度**低**：只需遍历订单簿对手方深度，按价格优先成交
- 滑点可自然涌现于订单簿深度消耗过程中，无需外生模型
- 需限制单笔市价单的最大数量/金额（`maxMktQty`），防止"胖手指"错误

---

### 8.2 止盈止损与条件单

#### 触发逻辑

止盈单（Take Profit）和止损单（Stop Loss）本质上是**条件单**：

- **止损（Stop Loss）**：当价格向亏损方向移动到触发价时，自动提交执行单以平仓
- **止盈（Take Profit）**：当价格向盈利方向移动到触发价时，自动提交执行单以平仓

**方向规则**（以现货为例）：
- STOP_LOSS BUY：触发价必须 **高于** 当前价（用于空头止损/突破买入）
- STOP_LOSS SELL：触发价必须 **低于** 当前价（用于多头止损）
- TAKE_PROFIT BUY：触发价必须 **低于** 当前价
- TAKE_PROFIT SELL：触发价必须 **高于** 当前价

#### 触发价 vs 执行价

| 概念 | 说明 |
|------|------|
| **Trigger Price（触发价）** | 订单从"休眠"转为"活跃"的阈值价格。到达此价格后，订单被提交到市场 |
| **Execution Price（执行价）** | 订单实际成交的价格。Stop-Market 为市场最优价（可能有滑点）；Stop-Limit 为用户设定的限价 |

#### 市价 TP/SL vs 限价 TP/SL

| 类型 | 触发后行为 | 优点 | 缺点 |
|------|-----------|------|------|
| **Stop-Market** | 转为市价单，立即以最优价执行 | 保证成交 | 极端行情下可能以很差价格成交 |
| **Stop-Limit** | 转为限价单，按设定限价挂簿 | 价格可控 | 若价格快速穿过限价，可能无法成交（"穿价风险"） |

#### 触发条件：三种价格类型

| 价格类型 | Binance | OKX | Bybit |
|----------|---------|-----|-------|
| **Last Price（最新成交价）** | 现货默认；期货 `workingType=CONTRACT_PRICE` | `triggerType=last` | `tpTriggerBy=LastPrice` |
| **Mark Price（标记价格）** | 期货 `workingType=MARK_PRICE` | `triggerType=mark`（推荐） | `tpTriggerBy=MarkPrice` |
| **Index Price（指数价格）** | — | `triggerType=index` | `tpTriggerBy=IndexPrice` |

合约交易中通常推荐用 **Mark Price** 触发，以避免单一交易所的极端价格操纵导致意外触发。

#### 条件单的订单状态流转

```
用户提交 Stop-Limit 单
    ↓
交易所验证参数
    ↓
订单进入 UNTRIGGERED 状态，由条件单引擎监控
    ↓
监控价格（Last/Mark/Index）触及触发价
    ↓
条件单引擎提交对应的限价单/市价单到匹配引擎
    ↓
子订单进入订单簿（NEW），等待撮合
    ↓
成交（FILLED）或取消（CANCELLED/EXPIRED）
```

#### 对仿真环境的启示

- **实现难度中低**：维护一个未触发的条件单列表，每个 tick 检查价格是否触及触发价
- **需要额外状态**：条件单的状态机（`UNTRIGGERED` → `TRIGGERED` → `NEW` → ...）
- **需要价格源抽象**：定义 `PriceOracle` 接口，提供 `last` / `mark` / `index` 三种价格
- **资金冻结**：条件单触发后会生成子订单，需要预留资金。不同交易所策略不同：Binance 现货止损限价单会预先冻结相应资产

---

### 8.3 OCO 订单

OCO（One-Cancels-Other）将**两个订单绑定为一组**：

- **Leg A**：一个限价单（通常是止盈方向，如 `LIMIT_MAKER`）
- **Leg B**：一个止损限价单（`STOP_LOSS_LIMIT`）

两个订单共享相同的 `side`（同为 BUY 或 SELL）和 `quantity`。

#### 核心规则

**一个订单的任何成交（包括部分成交）都会立即触发另一个订单的取消**。用户手动取消其中一个订单，**整个 OCO 组**都会被取消。

以 Binance 现货 OCO 为例：
```
OCO 订单组提交
    ├── 限价单 @ $60,000 (止盈)
    └── 止损限价单: 触发价 $48,000, 限价 $47,500 (止损)

情况1：价格涨到 $60,000，限价单成交 → 止损单自动取消
情况2：价格跌到 $48,000，止损单触发为限价单 → 止盈限价单自动取消
```

#### 资金冻结机制

| 交易所 | 冻结策略 |
|--------|---------|
| **Binance 现货** | OCO 的两个订单都需要冻结资金，但由于是同一方向且只执行其一，交易所实际按**订单总量冻结一次**（不会重复冻结两倍金额） |
| **OKX** | OCO algo order 冻结逻辑类似，按实际可能成交的最大量预留 |
| **Bybit 合约** | TP/SL 通过 `trading-stop` 设置时，**不预先冻结额外资金**，而是占用仓位对应的保证金 |

#### 对仿真环境的启示

- **实现难度中低**：给订单增加 `group_id` 字段，一个订单成交时遍历同组订单并取消
- **资金冻结简化策略**：OCO 组只冻一份资金（取两单中需要冻结的较大者）
- **分层架构**：将订单簿核心（限价单匹配）与条件单引擎（OCO/TP/SL）分离

---

### 8.4 跟踪止损

跟踪止损（Trailing Stop）是一种**动态条件单**，其触发价会随着市场价格向有利方向移动而自动调整。

#### 核心参数

| 参数 | Binance 期货 | OKX | Bybit |
|------|-------------|-----|-------|
| **激活价** | `activatePrice` | `activePx` | — |
| **回调幅度** | `callbackRate`（百分比） | `callbackRatio` | — |
| **固定价差** | — | `callbackSpread` | `trailingAmount` |

#### 跟随调整机制

以 **多头 Trailing Stop Sell** 为例：

1. **初始状态**：BTC 价格 $50,000，设置 `callbackRate = 2%`
   - 初始触发价 = $50,000 × (1 − 2%) = $49,000

2. **价格上涨**：BTC 涨到 $55,000
   - 触发价跟随上调到 $55,000 × (1 − 2%) = $53,900

3. **价格回调**：BTC 从 $55,000 回落到 $53,500（低于 $53,900）
   - **触发！** 提交市价卖单

**关键特性**：触发价只向有利方向移动（对多头只上调不下调），一旦价格回落达到回调幅度即触发。

#### 现货 vs 合约支持情况

| 交易所 | 现货 Trailing Stop | 合约 Trailing Stop |
|--------|-------------------|-------------------|
| **Binance** | ❌ 不支持 | ✅ `TRAILING_STOP_MARKET` |
| **OKX** | ✅ `move_order_stop` | ✅ `move_order_stop` |
| **Bybit** | ✅ 近年已支持 | ✅ 通过 `trading-stop` |

#### 对仿真环境的启示

- **实现难度中高**：需要为每个 Trailing Stop 维护动态触发价状态（`peak_price` / `current_trigger_price`）
- 建议每个 tick 更新时重新计算触发价
- 可先实现百分比回调模式（`callbackRate`），固定价差模式后续添加

---

### 8.5 杠杆与保证金

#### 杠杆交易基础

杠杆交易是指交易者通过向交易所借入资金，以**自有资金作为保证金**，控制远超自身资本规模的仓位。

| 概念 | 定义 | 计算方式 |
|------|------|----------|
| **初始保证金（IM）** | 开仓所需的最低保证金 | `IM = 仓位名义价值 × 初始保证金率 = 仓位名义价值 / 杠杆倍数` |
| **维持保证金（MM）** | 维持仓位不爆仓的最低权益 | `MM = 仓位名义价值 × 维持保证金率` |

#### 逐仓模式（Isolated Margin）

- 每个交易对/仓位拥有**独立的保证金池**
- 爆仓时只损失该仓位的保证金，不影响其他仓位
- 适合：初学者、单仓位风险管理者

#### 全仓模式（Cross Margin）

- 全账户所有资产共享一个**统一的保证金池**
- 盈亏互抵：一个仓位的盈利可以抵消另一个仓位的亏损
- 爆仓连锁风险：若保证金水平跌破阈值，所有仓位可能被强制平仓
- 支持**自动借币**（Auto-Borrow）：余额不足时自动借入资产完成交易

#### 各交易所保证金公式对比

| 交易所 | 保证金率公式 | 清算阈值 |
|--------|-------------|----------|
| **Binance 全仓** | `总资产价值 / (总负债 + 累计利息)` | ≤ 1.1 |
| **Binance 逐仓** | `仓位资产 / (仓位负债 + 累计利息)` | 依交易对而定 |
| **OKX** | `mgnRatio = adjEq / mmr` | ≤ 1.0 |
| **Bybit UTA** | 统合计算（类似 OKX） | 依模式而异 |

#### 借贷与利息

- **计息周期**：大多数交易所按小时计息，不足 1 小时按 1 小时计算
- **利息公式**：`每小时利息 = 借入金额 × (日利率 / 24)`
- **利率类型**：浮动利率（根据资产供需动态调整）为主，Bybit UTA 2026 年推出固定利率借贷

#### 现货杠杆 vs 合约杠杆

| 维度 | 现货杠杆 | 合约杠杆 |
|------|---------|---------|
| 资产交割 | 有实际资产交割 | 无实际资产交割 |
| 做空机制 | 需先借入 base 资产再卖出 | 直接卖出合约即可 |
| 利息/资金费 | 按小时收取借贷利息 | 永续合约每 8 小时收取 Funding Rate |
| 最大杠杆 | 通常 3x–20x | 可达 50x–125x |

#### 对仿真环境的启示

支持杠杆仿真的交易环境需要引入以下**额外状态**：

| 状态变量 | 说明 |
|----------|------|
| `margin_mode` | `ISOLATED` / `CROSS` |
| `leverage` | 当前杠杆倍数 |
| `total_equity` | 账户总权益 |
| `adjusted_equity` | 有效保证金 |
| `total_borrowed` | 各资产借入本金 |
| `total_interest` | 各资产累计未还利息 |
| `liabilities` | 总负债 = borrowed + interest |

---

### 8.6 永续合约

永续合约（Perpetual Swap）是一种**没有到期日**的衍生品合约，由 BitMEX 于 2016 年首创，现已成为加密货币市场交易量最大的衍生品。

#### 核心区别

| 特性 | 交割期货 | 永续合约 |
|------|----------|----------|
| 到期日 | 有 | 无 |
| 价格收敛机制 | 到期时基差收敛至 0 | 资金费率（Funding Rate）每 8 小时结算 |
| 持仓时间 | 有限 | 无限 |

#### 资金费率（Funding Rate）

资金费率是永续合约的核心机制，用于在多空双方之间定期进行价值转移，使永续合约价格收敛于现货指数价格。

**通用公式**：

$$\text{Funding Rate} = \text{Premium Index} + \text{Clamp}(\text{Interest Rate} - \text{Premium Index}, \text{上限}, \text{下限})$$

**Binance 公式**：

$$\text{Funding Rate} = \text{Average Premium Index} + \text{Clamp}(\text{Interest Rate} - \text{Average Premium Index}, 0.05\%, -0.05\%)$$

其中 Interest Rate 固定为 $0.03\%/\text{天} = 0.01\%/\text{8小时}$。

**收取周期**：通常每 8 小时（UTC 0:00, 8:00, 16:00）。当资金费率触及上限/下限时，OKX 可**自动**将周期缩短至 1 小时，Binance 需手动调整。

**支付方向**：
- 资金费率 > 0：多头支付给空头（市场看涨）
- 资金费率 < 0：空头支付给多头（市场看跌）

**资金费计算**：

$$\text{Funding Fee} = \text{Position Nominal Value} \times \text{Funding Rate}$$

#### 标记价格（Mark Price）

标记价格是用于计算未实现盈亏（UPnL）和触发强平的"公允价格"，通过算法平滑处理，避免被单一交易所的短期价格波动操纵。

**Binance 标记价格（永续合约）**：

$$\text{Mark Price} = \text{Median}(\text{Price 1}, \text{Price 2}, \text{Contract Price})$$

其中：
- Price 1 = 指数价格（Index Price）
- Price 2 = 指数价格 + 30 秒基差移动平均
- Contract Price = 本交易所合约最新成交价

**为什么用标记价格计算强平？** 防止价格操纵、避免闪崩误杀、保护交易者。

#### 强平机制（Liquidation）

**触发条件**：

$$\text{Margin Ratio} \geq 100\% \quad \text{或等价地} \quad \text{Mark Price reaches Liquidation Price}$$

**强平过程**：
1. 取消该仓位所有未成交订单（释放冻结保证金）
2. 以市价单形式在市场中平仓
3. 若市价平仓无法完全成交或产生穿仓损失：
   - 优先使用 **保险基金（Insurance Fund）** 弥补损失
   - 若保险基金不足，触发 **自动减仓（ADL）**

**ADL（Auto-Deleveraging）排序规则**：

$$\text{ADL Priority} = \text{PnL Percentage} \times \text{Leverage}$$

按盈利和杠杆倍数对所有盈利用户排序，优先选择 **盈利最多且杠杆最高** 的用户进行强制平仓。

#### 未实现盈亏（Unrealized PnL）

**U本位合约**：

$$\text{UPnL} = (\text{Mark Price} - \text{Entry Price}) \times \text{Position Size}$$

**币本位合约**：

$$\text{UPnL} = (\frac{1}{\text{Entry Price}} - \frac{1}{\text{Mark Price}}) \times \text{Position Size} \times \text{Contract Face Value}$$

#### 对仿真环境的启示

永续合约仿真需要以下核心状态：

| 状态变量 | 说明 |
|----------|------|
| `funding_rate` | 当前资金费率 |
| `mark_price` | 标记价格（用于 UPnL 和强平） |
| `index_price` | 指数价格（多交易所加权模拟） |
| `next_funding_time` | 下次资金结算时间戳 |
| `insurance_fund` | 保险基金余额（平台级） |
| `position_size` / `entry_price` | 仓位大小和开仓均价 |
| `liquidation_price` | 强平价格（动态更新） |
| `margin_mode` / `leverage` | 保证金模式和杠杆 |

---

### 8.7 交割期货

交割期货（Delivery / Quarterly Futures）与永续合约的核心区别在于**有固定的到期日和交割日**。

#### 到期周期

| 周期类型 | 说明 | 代表交易所 |
|---------|------|-----------|
| **周合约** | 每周五到期 | OKX |
| **月度合约** | 每月最后一个周五到期 | CME、OKX |
| **季度合约** | 3月、6月、9月、12月最后一个周五 | Binance、OKX、Deribit |

#### 交割方式

- **现金交割（Cash Settlement）**：绝大多数数字货币交割期货采用，以到期时的交割价格结算差额。Binance、OKX、Deribit 均为此方式。
- **实物交割（Physical Delivery）**：少数合约支持，如 Bakkt（ICE 旗下）比特币期货。

**交割价格确定**：
- Binance：到期前最后 1 小时（7:00–8:00 UTC）每秒指数价格的算术平均值
- OKX：2026 年 3 月起，到期前 30 分钟指数价格的算术平均，每 200ms 采样一次
- CME：基于 CF Benchmarks 的比特币参考汇率（BRR）

#### 到期前行为与流动性特征

1. **自动平仓**：到期日 UTC 08:00，所有未平仓头寸由交易所自动以交割价格结算
2. **展期（Roll）**：卖出近月合约、买入远月合约，维持市场敞口
3. **基差收敛**：到期前期货价格必然向现货价格收敛，$\text{Basis} = \text{期货价格} - \text{现货价格} \to 0$
4. **流动性变化**：临近到期时，近月合约流动性显著下降，买卖价差扩大

#### 对仿真环境的启示

- 到期事件属于**确定性 Chance Node**（时间驱动，非随机）
- 需要在环境 `step()` 中检查当前时间是否触发到期
- 到期时所有 Agent 的对应持仓同时被结算，属于同步状态转移
- 仿真中的期货价格 = 现货价格 + 基差（随时间衰减），到期时基差强制归零

---

### 8.8 期权

数字货币期权市场以**欧式现金结算**为主，Deribit 占据约 90% 市场份额。

#### 基本类型

| 类型 | 说明 | 适用场景 |
|-----|------|---------|
| **看涨期权（Call）** | 买方有权以行权价买入标的 | 看多、对冲空头 |
| **看跌期权（Put）** | 买方有权以行权价卖出标的 | 看空、对冲多头 |
| **欧式期权（European）** | 仅到期日可行权 | Deribit、OKX、Binance、Bybit 主流产品 |
| **美式期权（American）** | 到期前任何时间可行权 | 少数交易所提供 |

#### 期权核心要素

| 要素 | 说明 |
|------|------|
| **标的资产** | BTC、ETH、SOL 等 |
| **行权价（Strike）** | 约定的买卖价格 |
| **到期日（Expiry）** | 期权失效日期，通常为每周五 08:00 UTC |
| **权利金（Premium）** | 买方支付给卖方的价格 |

#### 期权定价：Black-Scholes-Merton 模型

$$C = S_0 N(d_1) - K e^{-rT} N(d_2)$$

$$P = K e^{-rT} N(-d_2) - S_0 N(-d_1)$$

其中 $S_0$ 为标的现货价格，$K$ 为行权价，$T$ 为剩余期限，$r$ 为无风险利率，$\sigma$ 为隐含波动率，$N(\cdot)$ 为标准正态分布 CDF。

**在数字货币市场的局限**：
- BSM 假设收益率对数正态分布，但加密市场存在厚尾（Fat Tails）和价格跳跃
- BSM 系统性地**低估**比特币期权价格，尤其对深度实值合约
- 改进模型：Heston（随机波动率）、Merton 跳跃扩散、Bates 模型

#### 希腊字母（Greeks）

| Greek | 定义 | 交易意义 |
|-------|------|---------|
| **Delta ($\Delta$)** | 期权价格对标的价格的敏感度 | 方向敞口、对冲比率 |
| **Gamma ($\Gamma$)** | Delta 对标的价格的二阶导 | 对冲调整频率，ATM 近月最高 |
| **Theta ($\Theta$)** | 时间衰减（每日） | 持有成本，近月 ATM 最大 |
| **Vega ($\mathcal{V}$)** | 对隐含波动率的敏感度 | 波动率敞口，远月 ATM 最高 |

#### 期权盈亏与行权

| 头寸 | 到期盈亏公式 |
|-----|-----------|
| 买入看涨（Long Call） | $\max(0, S_T - K) - \text{Premium}$ |
| 买入看跌（Long Put） | $\max(0, K - S_T) - \text{Premium}$ |
| 卖出看涨（Short Call） | $\text{Premium} - \max(0, S_T - K)$ |
| 卖出看跌（Short Put） | $\text{Premium} - \max(0, K - S_T)$ |

- 实值期权（ITM）：到期自动行权，现金结算差额
- 虚值期权（OTM）：到期自动作废
- 买入期权仅需支付权利金，最大损失已锁定
- 卖出期权需缴纳保证金，潜在损失理论上无限（Call）或很大（Put）

#### 组合策略

| 策略 | 结构 | 特征 |
|------|------|------|
| **保护性看跌（Protective Put）** | 持有现货 + 买入看跌 | 下行风险锁定，上行无限 |
| **备兑看涨（Covered Call）** | 持有现货 + 卖出看涨 | 震荡市获取额外收益 |
| **跨式组合（Straddle）** | 同时买入相同行权价的 Call 和 Put | 方向中性，押注高波动 |

#### 对仿真环境的启示

- 期权仿真需要新增：**期权定价引擎（BSM + Greeks）**、**合约生命周期管理**、**到期行权处理器**
- 到期时批量处理所有期权合约，实值自动行权，现金结算
- Greeks 可作为 Agent 观察空间的市场状态特征
- 组合保证金需考虑头寸间的对冲效应（如 Delta 中性组合降低保证金要求）

---

### 8.9 功能实现优先级建议

基于实现难度和对仿真环境的增强价值，建议按以下优先级扩展：

| 优先级 | 功能 | 实现难度 | 价值 | 关键新增状态/模块 |
|--------|------|----------|------|-----------------|
| **P1** | 市价单 | ⭐ 低 | 高 | 订单簿遍历撮合逻辑（已具备） |
| **P1** | Stop-Market / TP-Market | ⭐⭐ 中低 | 高 | 条件单引擎 + 未触发订单列表 |
| **P1** | IOC / FOK | ⭐⭐ 中低 | 高 | `time_in_force` 字段 + 撮合后剩余量处理 |
| **P2** | Stop-Limit / TP-Limit | ⭐⭐⭐ 中 | 高 | 母单→子单映射关系 |
| **P2** | OCO 订单 | ⭐⭐⭐ 中 | 中 | `OrderGroup` + 成交事件监听器 |
| **P2** | 杠杆（逐仓） | ⭐⭐⭐⭐ 中高 | 高 | 仓位层状态 + 保证金计算模块 |
| **P3** | 永续合约 | ⭐⭐⭐⭐⭐ 高 | 高 | Funding Rate、Mark Price、Insurance Fund、ADL |
| **P3** | 全仓杠杆 | ⭐⭐⭐⭐⭐ 高 | 中 | 跨仓位保证金共享 + 连锁强平 |
| **P4** | Trailing Stop | ⭐⭐⭐⭐ 中高 | 中 | 动态触发价状态 + 峰值价格追踪 |
| **P4** | 交割期货 | ⭐⭐⭐⭐ 中高 | 中 | 合约生命周期管理 + 到期结算引擎 |
| **P5** | 期权 | ⭐⭐⭐⭐⭐ 高 | 低（当前阶段）| BSM 定价引擎 + Greeks 计算 + 行权处理器 |

**分阶段路线图建议**：

- **Phase 1（现货增强）**：市价单 + IOC/FOK + Stop-Market/TP-Market
- **Phase 2（高级订单）**：Stop-Limit + OCO + Trailing Stop
- **Phase 3（杠杆现货）**：逐仓杠杆 + 借贷利息 + 强平引擎
- **Phase 4（衍生品）**：永续合约（U本位 + 单向模式）
- **Phase 5（完整生态）**：交割期货 + 双向模式 + 全仓保证金 + 期权
