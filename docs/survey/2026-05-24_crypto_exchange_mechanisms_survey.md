# 主流数字货币交易所交易机制深度调研报告

> 调研目标：为 TradeMasterOnline 的交易仿真环境设计提供真实交易所的运行机制参考，深入理解撮合引擎、订单簿、自成交保护、资金冻结、手续费结算等核心概念的业界实现细节。
>
> 本报告基于 Binance、OKX、Bybit、Coinbase、Kraken 等主流交易所的官方 API 文档和交易规则，辅以 FIX 协议标准、ABIDES/PyMarketSim/JaxMARL-HFT 等学术仿真框架的公开资料。所有引用均来自真实文档。
>
> **组织原则**：本报告按交易机制的内在逻辑层次组织，从市场基础设施到订单类型、资金模型、衍生品机制逐层展开。每一章均力求中立地呈现业界现状、各交易所差异及学术参考。

---

## 目录

- [1. 范围与方法](#1-范围与方法)
- [2. 交易所运行全景](#2-交易所运行全景)
  - [2.1 市场结构层次](#21-市场结构层次)
  - [2.2 交易产品谱系](#22-交易产品谱系)
  - [2.3 核心机制总览](#23-核心机制总览)
- [3. 撮合引擎与订单簿](#3-撮合引擎与订单簿)
  - [3.1 限价订单簿（LOB）](#31-限价订单簿lob)
  - [3.2 撮合算法](#32-撮合算法)
  - [3.3 成交价规则](#33-成交价规则)
  - [3.4 订单簿数据结构实现](#34-订单簿数据结构实现)
- [4. 订单类型体系](#4-订单类型体系)
  - [4.1 基础订单类型](#41-基础订单类型)
  - [4.2 条件订单类型](#42-条件订单类型)
  - [4.3 组合订单类型](#43-组合订单类型)
  - [4.4 订单生命周期与状态机](#44-订单生命周期与状态机)
  - [4.5 Time in Force 策略](#45-time-in-force-策略)
- [5. 自成交保护（STP）](#5-自成交保护stp)
  - [5.1 动机与定义](#51-动机与定义)
  - [5.2 STP 策略类型](#52-stp-策略类型)
  - [5.3 触发条件与识别粒度](#53-触发条件与识别粒度)
  - [5.4 各交易所实现对比](#54-各交易所实现对比)
- [6. 余额与资金模型](#6-余额与资金模型)
  - [6.1 经典分离账户](#61-经典分离账户)
  - [6.2 统一账户体系](#62-统一账户体系)
  - [6.3 资金冻结逻辑](#63-资金冻结逻辑)
  - [6.4 跨交易对资金共享](#64-跨交易对资金共享)
- [7. 手续费与结算](#7-手续费与结算)
  - [7.1 Maker-Taker 模型](#71-maker-taker-模型)
  - [7.2 Received-Asset 扣除](#72-received-asset-扣除)
  - [7.3 费率结构与折扣](#73-费率结构与折扣)
- [8. 价格与数量约束](#8-价格与数量约束)
  - [8.1 Filter 体系](#81-filter-体系)
  - [8.2 价格保护机制](#82-价格保护机制)
- [9. 衍生品特有机制](#9-衍生品特有机制)
  - [9.1 杠杆与保证金](#91-杠杆与保证金)
  - [9.2 永续合约](#92-永续合约)
  - [9.3 交割期货](#93-交割期货)
  - [9.4 期权](#94-期权)
- [10. 交易所实现分析](#10-交易所实现分析)
  - [10.1 Binance](#101-binance)
  - [10.2 OKX](#102-okx)
  - [10.3 Bybit](#103-bybit)
  - [10.4 Coinbase](#104-coinbase)
  - [10.5 Kraken](#105-kraken)
  - [10.6 传统交易所（Nasdaq/NYSE/CME）](#106-传统交易所nasdaqnysecme)
- [11. 横向对比矩阵](#11-横向对比矩阵)
- [12. 学术仿真与行业标准](#12-学术仿真与行业标准)
  - [12.1 开源仿真框架谱系](#121-开源仿真框架谱系)
  - [12.2 FIX 协议标准](#122-fix-协议标准)
  - [12.3 传统交易所 vs 数字货币交易所](#123-传统交易所-vs-数字货币交易所)
- [13. 完整功能全景与实现优先级建议](#13-完整功能全景与实现优先级建议)
  - [13.1 功能全景分类](#131-功能全景分类)
  - [13.2 优先级排序](#132-优先级排序)
  - [13.3 对 TradeMasterOnline 的设计建议](#133-对-trademasteronline-的设计建议)
- [14. 参考资料](#14-参考资料)

---

## 1. 范围与方法

### 调研范围

本次调研聚焦于**中心化交易所（CEX）**的核心交易机制，覆盖以下维度：

1. **撮合引擎（Matching Engine）**：价格优先、时间优先的具体实现，订单簿数据结构，撮合算法变体
2. **订单类型体系**：从基础限价单到复杂条件单、组合单的完整谱系
3. **自成交保护（Self-Trade Prevention, STP）**：策略类型、默认行为、触发条件、跨账户/组支持
4. **余额与资金冻结模型**：`free`/`locked` 定义、下单冻结逻辑、跨交易对资金共享、统一账户
5. **手续费结算模式**：received-asset 扣除、Maker/Taker 区分、费率结构
6. **订单生命周期与 Time in Force**：状态流转，GTC/IOC/FOK/Post-Only 等行为
7. **价格与数量限制**：tick size、step size、min notional 等 filter 校验，价格保护机制
8. **衍生品特有机制**：杠杆、保证金、永续合约资金费率、交割期货、期权

**明确排除**：
- 链上结算与清算细节（DEX 相关）
- 交易所级别的合规风控（如反洗钱、KYC）
- 具体交易算法或策略（如做市、套利）

### 调研方法

1. **官方文档抓取**：直接抓取各交易所 GitHub/API 文档仓库中的 REST API 定义、FAQ、交易规则
2. **多源交叉验证**：对同一机制查阅多个交易所的文档，识别共性与差异
3. **学术文献补充**：查阅 ABIDES、PyMarketSim、JaxMARL-HFT 等开源仿真框架论文，以及市场微观结构经典文献
4. **行业标准对照**：参考 FIX 协议（Tag 7928 SelfTradeType）中关于 STP 和撮合的标准定义

### 调研对象优先级

| 优先级 | 交易所/机构 | 理由 |
|--------|------------|------|
| P0 | Binance | 交易量全球第一，API 文档最详尽，STP 机制透明 |
| P0 | OKX | 统一账户体系最具代表性，API 设计清晰，订单类型丰富 |
| P1 | Bybit | 衍生品起家，现货发展迅速，SMP 文档透明 |
| P1 | Coinbase | 美国最大合规交易所，费率结构与传统金融接近 |
| P2 | Kraken | 老牌交易所，FIX 协议支持好，STP 参数简洁 |
| P2 | Nasdaq / NYSE / CME | 传统交易所撮合规则，提供 STP 行业标准参照 |

---

## 2. 交易所运行全景

### 2.1 市场结构层次

中心化交易所的市场结构可抽象为三层：

| 层次 | 职责 |
|------|------|
| **用户层** | 接收订单提交、取消、修改请求，进行参数校验和身份认证 |
| **撮合层** | 维护订单簿，执行撮合算法，处理自成交保护，生成成交记录 |
| **结算层** | 更新用户余额（冻结/释放/增减），扣除手续费，维护持仓状态 |

### 2.2 交易产品谱系

| 产品类型 | 说明 | 代表交易所 |
|---------|------|-----------|
| **现货（Spot）** | 即时交割，资产所有权转移 | 全部 |
| **杠杆现货（Margin）** | 借入资金交易，有实际资产交割 | Binance、OKX、Kraken |
| **永续合约（Perpetual Swap）** | 无到期日，资金费率锚定现货 | Binance、OKX、Bybit |
| **交割期货（Delivery Futures）** | 有固定到期日，现金交割 | Binance、OKX、CME |
| **期权（Options）** | 欧式现金结算为主 | Deribit（~90% 市场份额）、OKX、Binance |

### 2.3 核心机制总览

以下机制是所有交易产品共用的基础设施：

| 机制 | 作用 | 复杂度 |
|------|------|--------|
| 限价订单簿（LOB） | 维护未成交订单，提供市场深度 | 中 |
| 撮合引擎 | 执行价格优先时间优先匹配 | 中 |
| 自成交保护（STP） | 防止同一实体自买自卖 | 中 |
| 资金冻结 | 确保未成交订单有足够的资金支撑 | 中 |
| 手续费结算 | 激励流动性提供，覆盖运营成本 | 低 |
| Filter 校验 | 维护市场秩序，防止错误订单 | 低 |

以下机制主要出现在衍生品中：

| 机制 | 作用 | 复杂度 |
|------|------|--------|
| 保证金计算 | 控制杠杆风险 | 高 |
| 资金费率（Funding Rate） | 使永续合约价格收敛现货 | 高 |
| 标记价格（Mark Price） | 公允价格用于强平和 UPnL | 高 |
| 强平与 ADL | 风险传导与处置 | 高 |
| 期权定价（BSM/Greeks） | 权利金计算与风险管理 | 很高 |

---

## 3. 撮合引擎与订单簿

### 3.1 限价订单簿（LOB）

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

### 3.2 撮合算法

撮合引擎（Matching Engine）是交易所的核心交易执行系统，负责将 incoming order 与订单簿中的 resting order 进行匹配。

#### 价格优先、时间优先（Price-Time Priority, FIFO）

这是绝大多数交易所（包括所有调研的数字货币交易所）采用的撮合规则：

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

#### Pro-Rata（按比例分配）

部分衍生品市场（如 CME 某些产品）采用 Pro-Rata 算法：同一价格档内，订单按 resting size 的比例分配成交量。这种算法鼓励大额挂单，但对散户的公平性较低。

| 算法 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| **Price-Time Priority** | 现货、零售市场 | 简单、公平、透明 | 偏向速度型交易者 |
| **Pro-Rata** | 期货、衍生品、机构市场 | 奖励大额订单，加深订单簿 | 对散户公平性较低 |
| **Hybrid** | LP 重度参与的场所 | 灵活、可定制 | 管理复杂 |

> 所有调研的数字货币交易所（Binance、OKX、Bybit、Coinbase、Kraken）现货和合约均采用 **Price-Time Priority**。

#### 其他撮合算法变体

| 算法 | 说明 | 使用场所 |
|------|------|---------|
| **Size-Time Priority** | 同时考虑订单大小和到达时间 | 部分机构场所 |
| **LIFO（Last-In-First-Out）** | 最新到达的订单优先成交 | 极少数高速场所 |
| **Maximize Volume** | 略微延迟以匹配更大成交量 | 特定集合竞价场景 |

### 3.3 成交价规则

- incoming 限价单/市价单 与 resting 限价单 成交时，**以 resting 订单的价格作为成交价**
- 这是行业通用规则，确保 resting order 获得其指定的价格

**Order Amend Keep Priority**：
- Binance 支持修改未成交订单的数量而不丢失时间优先权
- 这与传统的 cancel-replace（取消后重新排队）不同，后者会重置时间戳

### 3.4 订单簿数据结构实现

生产级撮合引擎通常采用以下数据结构组合：

| 数据结构 | 作用 | 复杂度 |
|---------|------|--------|
| **平衡树（如红黑树）** | 管理价格档位，支持快速插入/删除 | $O(\log n)$ |
| **FIFO 队列** | 每个价格档内维护时间优先顺序 | $O(1)$ 入队/出队 |
| **哈希表** | 订单 ID 到订单对象的 $O(1)$ 索引，支持快速取消/修改 | $O(1)$ |

PyMarketSim（2024）采用 **4-Heap** 数据结构实现 LOB，在 $10^6$ 订单规模下平均操作时间低于 0.005 毫秒。

---

## 4. 订单类型体系

订单类型可按复杂度分为三层：基础订单、条件订单、组合订单。

### 4.1 基础订单类型

| 类型 | 说明 | 角色 |
|------|------|------|
| **LIMIT（限价单）** | 以指定价格或更优价格成交，未成交部分入簿 | 通常是 Maker |
| **MARKET（市价单）** | 以当前市场上最优可得价格立即成交 | 总是 Taker |
| **LIMIT_MAKER** | 仅作为 Maker 挂单的限价单，若会立即成交则拒绝 | 强制 Maker |

**市价单的执行机制**：

市价单的核心逻辑是**立即以当前市场上最优可得价格成交**。当用户提交市价单后，交易所匹配引擎会将其与订单簿中对手方的最优挂单进行撮合：

- **买方向**：从订单簿的最低 ask 价格开始，逐层向上吃单，直到订单全部成交或订单簿该方向深度耗尽
- **卖方向**：从订单簿的最高 bid 价格开始，逐层向下吃单

市价单**不保证成交价格**，但通常保证成交（在订单簿有深度的情况下）。若订单簿对手方深度不足，市价单可能只部分成交，剩余部分通常按 **IOC（Immediate Or Cancel）** 逻辑处理——未成交部分立即取消，不会作为挂单留在簿册中。

**市价单的下单方式差异**：

| 交易所 | 现货市价买入 | 现货市价卖出 | 说明 |
|--------|-------------|-------------|------|
| **Binance** | `quoteOrderQty`（如 100 USDT） | `quantity`（如 0.01 BTC） | 买入按 quote 金额，卖出按 base 数量 |
| **OKX** | `sz`（buy 时隐式为 quote 金额） | `sz`（base 数量） | 方向隐式区分语义 |
| **Bybit** | `qty`（buy 时为 quote 金额） | `qty`（base 数量） | 与 Binance 类似 |

**滑点（Slippage）**：

滑点是指订单期望成交价格与实际成交平均价格之间的偏差。产生原因：
1. **订单簿深度不足**：大额市价单会"穿透"多个价格层级
2. **高波动性**：从下单到撮合的极短时间内市场价格跳动
3. **网络延迟**：订单到达服务器时最优价已发生变化

### 4.2 条件订单类型

条件订单（Conditional Orders）在触发条件满足前处于"休眠"状态，由条件单引擎监控。

#### 止损（Stop Loss）与止盈（Take Profit）

| 类型 | 触发条件 | 触发后行为 |
|------|---------|-----------|
| **STOP_LOSS / TP_MARKET** | 价格触及触发价 | 转为市价单立即执行 |
| **STOP_LOSS_LIMIT / TP_LIMIT** | 价格触及触发价 | 转为限价单按设定价格挂簿 |

**方向规则**（以现货为例）：
- STOP_LOSS BUY：触发价必须 **高于** 当前价（用于空头止损/突破买入）
- STOP_LOSS SELL：触发价必须 **低于** 当前价（用于多头止损）
- TAKE_PROFIT BUY：触发价必须 **低于** 当前价
- TAKE_PROFIT SELL：触发价必须 **高于** 当前价

**触发价 vs 执行价**：

| 概念 | 说明 |
|------|------|
| **Trigger Price（触发价）** | 订单从"休眠"转为"活跃"的阈值价格 |
| **Execution Price（执行价）** | 订单实际成交的价格。Stop-Market 为市场最优价；Stop-Limit 为用户设定的限价 |

**市价 TP/SL vs 限价 TP/SL**：

| 类型 | 触发后行为 | 优点 | 缺点 |
|------|-----------|------|------|
| **Stop-Market** | 转为市价单，立即以最优价执行 | 保证成交 | 极端行情下可能以很差价格成交 |
| **Stop-Limit** | 转为限价单，按设定限价挂簿 | 价格可控 | 若价格快速穿过限价，可能无法成交（"穿价风险"） |

**触发条件：三种价格类型**：

| 价格类型 | Binance | OKX | Bybit |
|----------|---------|-----|-------|
| **Last Price（最新成交价）** | 现货默认；期货 `workingType=CONTRACT_PRICE` | `triggerType=last` | `tpTriggerBy=LastPrice` |
| **Mark Price（标记价格）** | 期货 `workingType=MARK_PRICE` | `triggerType=mark`（推荐） | `tpTriggerBy=MarkPrice` |
| **Index Price（指数价格）** | — | `triggerType=index` | `tpTriggerBy=IndexPrice` |

合约交易中通常推荐用 **Mark Price** 触发，以避免单一交易所的极端价格操纵导致意外触发。

#### 跟踪止损（Trailing Stop）

跟踪止损是一种**动态条件单**，其触发价会随着市场价格向有利方向移动而自动调整。

**核心参数**：

| 参数 | Binance 期货 | OKX | Bybit |
|------|-------------|-----|-------|
| **激活价** | `activatePrice` | `activePx` | — |
| **回调幅度** | `callbackRate`（百分比） | `callbackRatio` | — |
| **固定价差** | — | `callbackSpread` | `trailingAmount` |

**跟随调整机制**（以多头 Trailing Stop Sell 为例）：

1. **初始状态**：BTC 价格 $50,000，设置 `callbackRate = 2%$
   - 初始触发价 = $50,000 \times (1 - 2\%) = $49,000

2. **价格上涨**：BTC 涨到 $55,000
   - 触发价跟随上调到 $55,000 \times (1 - 2\%) = $53,900

3. **价格回调**：BTC 从 $55,000 回落到 $53,500（低于 $53,900）
   - **触发！** 提交市价卖单

**关键特性**：触发价只向有利方向移动（对多头只上调不下调），一旦价格回落达到回调幅度即触发。

**现货 vs 合约支持情况**：

| 交易所 | 现货 Trailing Stop | 合约 Trailing Stop |
|--------|-------------------|-------------------|
| **Binance** | ❌ 不支持 | ✅ `TRAILING_STOP_MARKET` |
| **OKX** | ✅ `move_order_stop` | ✅ `move_order_stop` |
| **Bybit** | ✅ 近年已支持 | ✅ 通过 `trading-stop` |

### 4.3 组合订单类型

#### OCO（One-Cancels-Other）

OCO 将**两个订单绑定为一组**：

- **Leg A**：一个限价单（通常是止盈方向，如 `LIMIT_MAKER`）
- **Leg B**：一个止损限价单（`STOP_LOSS_LIMIT`）

两个订单共享相同的 `side`（同为 BUY 或 SELL）和 `quantity`。

**核心规则**：
- **一个订单的任何成交（包括部分成交）都会立即触发另一个订单的取消**
- 用户手动取消其中一个订单，**整个 OCO 组**都会被取消

**资金冻结机制**：

| 交易所 | 冻结策略 |
|--------|---------|
| **Binance 现货** | OCO 的两个订单都需要冻结资金，但由于是同一方向且只执行其一，交易所实际按**订单总量冻结一次** |
| **OKX** | OCO algo order 冻结逻辑类似，按实际可能成交的最大量预留 |
| **Bybit 合约** | TP/SL 通过 `trading-stop` 设置时，**不预先冻结额外资金**，而是占用仓位对应的保证金 |

#### 冰山订单（Iceberg）

冰山订单只暴露部分数量到订单簿，隐藏部分在暴露部分成交后自动补充。OKX 支持此类型，Binance/Bybit 现货不支持。

### 4.4 订单生命周期与状态机

#### 标准订单状态流转

```
NEW → PARTIALLY_FILLED → FILLED
 ↓
CANCELED (by user / by OCO trigger / by system)
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
| `CANCELED` | 用户取消或系统取消 |
| `EXPIRED` | 按规则过期（IOC/FOK 未成交部分、STP 触发） |
| `REJECTED` | 被引擎拒绝 |
| `EXPIRED_IN_MATCH` | Binance 特有：因 STP 在撮合过程中过期 |

#### 条件订单的扩展状态流转

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

### 4.5 Time in Force 策略

Time in Force（TIF）定义订单在提交后的有效时间：

| 策略 | 缩写 | 行为 | 适用订单类型 |
|------|------|------|-------------|
| **Good Till Canceled** | GTC | 一直有效直到取消或完全成交 | 限价单 |
| **Immediate Or Cancel** | IOC | 立即成交可成交部分，剩余取消 | 限价单、市价单 |
| **Fill Or Kill** | FOK | 必须完全成交，否则全部取消 | 限价单 |
| **Post Only** | — | 仅作为 maker 挂单，若会立即成交则拒绝 | 限价单 |
| **Good Till Date** | GTD | 在指定日期/时间前有效 | 限价单（Coinbase 等） |

**Post-Only 与 Taker 的区分**：
- 提交限价单时，若价格越过当前 best 价（对买单而言高于 best ask，对卖单而言低于 best bid），则该单会立即成交，成为 Taker
- Post-Only 指令确保订单**不会**作为 Taker 成交，若判断会立即成交则直接拒绝

---

## 5. 自成交保护（STP）

### 5.1 动机与定义

自成交保护（Self-Trade Prevention, STP）是防止同一用户/账户的相反方向订单相互成交的机制。

**为什么需要 STP？**

1. **防止洗量（Wash Trading）**：同一主体自买自卖制造虚假成交量
2. **防止意外对冲**：策略误操作导致同一账户的订单互为对手方
3. **合规要求**：多数监管辖区要求交易所具备 STP 能力

**自成交的定义**：当 incoming order 的撮合对手方 resting order 属于**同一识别实体**时，构成自成交。

### 5.2 STP 策略类型

| 策略 | 行为描述 | 别名 | FIX Tag 7928 |
|------|----------|------|-------------|
| Cancel Newest / Expire Taker | 取消 incoming（新）订单 | EXPIRE_TAKER | `N` |
| Cancel Oldest / Expire Maker | 取消 resting（老）订单 | EXPIRE_MAKER | `O` |
| Cancel Both | 两个订单均取消 | EXPIRE_BOTH | `C` |
| Decrement | 双方减量，较小订单 expire | DECREMENT | `D` |
| Transfer | 同账户时等效 Decrement；跨账户同 Trade Group 时内部划转 | TRANSFER | — |
| None | 允许自成交 | NONE | `T` |

**Binance STP 行为规则**（来自官方 STP FAQ）：

STP 行为通常由 **taker order 的 STP mode** 决定，唯一的例外是 TRANSFER：

| Taker STP Mode | Maker STP Mode | Effective STP Mode |
|---------------|----------------|-------------------|
| `TRANSFER` | `TRANSFER` | `TRANSFER` |
| `TRANSFER` | 任何其他模式 | `DECREMENT` |
| `EXPIRE_MAKER` 等 | 任何模式 | Taker 的模式 |

### 5.3 触发条件与识别粒度

**触发条件**：
1. 两个订单方向相反（Buy vs Sell）
2. 价格交叉（ask <= bid 或反之）
3. 属于**同一识别实体**

**识别粒度（由粗到细）**：

| 粒度 | 说明 | 支持交易所 |
|------|------|-----------|
| **UID / 账户级别** | 同一用户的所有订单 | 全部 |
| **Trade Group / SMP Group** | 多个 UID 编为一组，组内互防 | Binance (`tradeGroupId`)、Bybit (SMP Trade Group) |
| **MPID + Trader ID** | 传统交易所的做市商识别码 | Nasdaq、NYSE |
| **Client ID** | 同一客户下的不同策略 | NYSE Pillar |

**STP 与部分成交**：

若 incoming order 在匹配过程中遇到多个 resting orders：
- 先与不触发 STP 的订单部分成交
- 当遇到触发 STP 的订单时，按 STP 策略处理剩余量
- 若整个价格档的所有 resting order 均触发 STP，则该档被清空，移至下一档

### 5.4 各交易所实现对比

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

> **关键发现**：Binance 现货和期货的默认 STP 策略为 **EXPIRE_MAKER**（2023 年 10 月起现货默认启用，2024 年 12 月起期货强制启用）。但不同交易对可能配置不同默认值，需通过 `exchangeInfo` 查询 `defaultSelfTradePreventionMode`。

---

## 6. 余额与资金模型

### 6.1 经典分离账户

大多数交易所的基础账户模型采用 `free` / `locked` 分离：

| 字段 | 含义 |
|------|------|
| `free` | 可用余额，可用于新订单、提现 |
| `locked` | 被未成交订单冻结的余额 |
| **总额** | `free + locked` |

**冻结逻辑**：
- **BUY 订单**：冻结 `price * quantity` 的 **quote 资产**
- **SELL 订单**：冻结 `quantity` 的 **base 资产**

**成交后的资金转移**：
- BUY 成交：quote 资产从 locked 扣除，base 资产增加到 free（扣除手续费后）
- SELL 成交：base 资产从 locked 扣除，quote 资产增加到 free（扣除手续费后）

### 6.2 统一账户体系

OKX、Bybit 等交易所推出的统一账户模型将现货、杠杆、合约、期权整合到一个账户体系下：

| 字段 | 含义 |
|------|------|
| `walletBalance` | 钱包余额（入金 + 已实现盈亏） |
| `equity` | 资产权益 = walletBalance − borrow + unrealized PnL |
| `availBal` / `availableToTrade` | 可用余额（可下单/转出的资金） |
| `frozenBal` / `locked` / `ordFrozen` | 被挂单冻结的余额 |
| `imr` | 初始保证金要求 |
| `mmr` | 维持保证金要求 |

统一账户的核心优势是**跨币种、跨产品共享保证金**，所有币种按汇率折算为 USD 计算可用保证金。

**OKX 账户模式**：
1. **Spot mode**：纯现货交易
2. **Futures mode**：期货独立保证金
3. **Multi-currency margin**：跨币种保证金
4. **Portfolio margin**：组合保证金（考虑 Delta 对冲效应）

### 6.3 资金冻结逻辑

**条件单的资金冻结**：

不同交易所对条件单（Stop/TP）的冻结策略不同：

| 交易所 | 条件单冻结策略 |
|--------|--------------|
| **Binance 现货** | 止损限价单会**预先冻结**相应资产 |
| **OKX** | 条件单触发后生成子订单时才冻结 |
| **Bybit 合约** | TP/SL 通过 `trading-stop` 设置时，**不预先冻结**，占用仓位保证金 |

**OCO 订单的资金冻结**：

由于 OCO 的两个订单只有一个会执行，交易所通常按**实际需要冻结的最大量**冻结一次，不会重复冻结两倍金额。

### 6.4 跨交易对资金共享

同一 quote 资产（如 USDT）在所有交易对中共享一个资金池；同一 base 资产（如 BTC）在所有交易对中也共享一个资金池。

**示例**：
- Agent 同时在 BTC/USDT 和 ETH/USDT 有未成交买单
- 两个买单都从同一个 USDT 资金池中扣除可用余额
- 若 USDT 总额不足以支撑两个买单之和，则第二个买单被拒绝

---

## 7. 手续费与结算

### 7.1 Maker-Taker 模型

- **Maker（做市商）**：提交限价单并进入订单簿等待成交的订单，提供流动性
- **Taker（吃单者）**：与订单簿中已有订单立即成交的订单，消耗流动性
- 通常 **Taker 费率 > Maker 费率**，以激励流动性提供

### 7.2 Received-Asset 扣除

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

### 7.3 费率结构与折扣

| 交易所 | Maker | Taker | 折扣机制 |
|--------|-------|-------|----------|
| **Binance** | 0.10% | 0.10% | BNB 抵扣 25% |
| **OKX** | 0.08% | 0.10% | OKB 折扣最高 40%，VIP7+ maker 负费率 |
| **Bybit** | 0.10% | 0.10% | — |
| **Coinbase** | 0.40%~0.60% | 0.60%~1.20% | 交易量阶梯递减 |
| **Kraken** | 0.16% | 0.26% | 交易量阶梯递减 |

> 注：Coinbase 费率显著高于其他交易所（约 4~6 倍），因其主打合规和美国零售市场。

---

## 8. 价格与数量约束

### 8.1 Filter 体系

交易所通过 filter 机制限制下单的价格和数量，以维护市场秩序。

| Filter | 字段 | 说明 | Binance 名称 |
|--------|------|------|-------------|
| 价格步长 | `tickSize` / `tickSz` | 价格必须是此值的整数倍 | PRICE_FILTER |
| 数量步长 | `stepSize` / `lotSz` / `qtyStep` | 数量必须是此值的整数倍 | LOT_SIZE |
| 最小名义价值 | `minNotional` / `minSz` | `price * quantity >= minNotional` | MIN_NOTIONAL |
| 价格范围 | `minPrice` / `maxPrice` | 价格必须在范围内 | PRICE_FILTER |
| 数量范围 | `minQty` / `maxQty` | 数量必须在范围内 | LOT_SIZE |
| 最大持仓 | `maxPosition` | 单个交易对最大持仓 | MAX_POSITION |

**验证规则**：
- `price % tickSize == 0`
- `quantity % stepSize == 0`
- `price * quantity >= minNotional`
- `minPrice <= price <= maxPrice`
- `minQty <= quantity <= maxQty`

### 8.2 价格保护机制

交易所为防止市价单在极端行情下以离谱价格成交，设置了多层保护：

| 机制 | 说明 | Binance | OKX | Bybit |
|------|------|---------|-----|-------|
| **价格涨跌幅限制** | 单时段内价格最大变动比例 | 期货支持 | 新上币 10 分钟后启用限价价格保护 | `priceLimitRatioX` / `priceLimitRatioY` |
| **市价单数量限制** | 单笔市价单最大数量/金额 | `MARKET_LOT_SIZE` / `NOTIONAL` | `maxMktSz` / `maxMktAmt` | `maxMktOrderQty` |
| **价格保护（Price Protect）** | 触发价偏离标记价时拒绝 | 期货 `priceProtect=true` | 通过限价逻辑实现 | 通过 `tpLimitPrice`/`slLimitPrice` 限制 |

---

## 9. 衍生品特有机制

### 9.1 杠杆与保证金

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
- **利率类型**：浮动利率（根据资产供需动态调整）为主

#### 现货杠杆 vs 合约杠杆

| 维度 | 现货杠杆 | 合约杠杆 |
|------|---------|---------|
| 资产交割 | 有实际资产交割 | 无实际资产交割 |
| 做空机制 | 需先借入 base 资产再卖出 | 直接卖出合约即可 |
| 利息/资金费 | 按小时收取借贷利息 | 永续合约每 8 小时收取 Funding Rate |
| 最大杠杆 | 通常 3x–20x | 可达 50x–125x |

### 9.2 永续合约

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

**收取周期**：通常每 8 小时（UTC 0:00, 8:00, 16:00）。当资金费率触及上限/下限时，OKX 可**自动**将周期缩短至 1 小时。

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

### 9.3 交割期货

交割期货（Delivery / Quarterly Futures）与永续合约的核心区别在于**有固定的到期日和交割日**。

#### 到期周期

| 周期类型 | 说明 | 代表交易所 |
|---------|------|-----------|
| **周合约** | 每周五到期 | OKX |
| **月度合约** | 每月最后一个周五到期 | CME、OKX |
| **季度合约** | 3月、6月、9月、12月最后一个周五 | Binance、OKX、Deribit |

#### 交割方式

- **现金交割（Cash Settlement）**：绝大多数数字货币交割期货采用，以到期时的交割价格结算差额
- **实物交割（Physical Delivery）**：少数合约支持，如 Bakkt（ICE 旗下）比特币期货

**交割价格确定**：
- Binance：到期前最后 1 小时（7:00–8:00 UTC）每秒指数价格的算术平均值
- OKX：2026 年 3 月起，到期前 30 分钟指数价格的算术平均，每 200ms 采样一次
- CME：基于 CF Benchmarks 的比特币参考汇率（BRR）

#### 到期前行为与流动性特征

1. **自动平仓**：到期日 UTC 08:00，所有未平仓头寸由交易所自动以交割价格结算
2. **展期（Roll）**：卖出近月合约、买入远月合约，维持市场敞口
3. **基差收敛**：到期前期货价格必然向现货价格收敛，$\text{Basis} = \text{期货价格} - \text{现货价格} \to 0$
4. **流动性变化**：临近到期时，近月合约流动性显著下降，买卖价差扩大

### 9.4 期权

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


---

## 10. 交易所实现分析

本节对每家交易所的核心机制实现进行逐节分析。分析维度包括：撮合引擎、STP、余额模型、手续费、订单类型、价格/数量限制。

### 10.1 Binance

**资源**：
- [Binance Spot REST API 文档](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md)
- [Binance STP FAQ](https://github.com/binance/binance-spot-api-docs/blob/master/faqs/stp_faq.md)
- [Binance API ENUM 定义](https://github.com/binance/binance-spot-api-docs/blob/master/enums.md)
- [Binance Order Amend Keep Priority](https://github.com/binance/binance-spot-api-docs/blob/master/faqs/order_amend_keep_priority.md)
- [Binance Trailing Stop FAQ](https://github.com/binance/binance-spot-api-docs/blob/master/faqs/trailing-stop-faq.md)

**撮合引擎**：
- 严格遵循**价格优先、时间优先**原则
- 支持 **Order Amend Keep Priority**：修改数量不丢失时间优先权
- `GET /api/v3/depth` 返回 bids 降序、asks 升序，每档为 `[价格, 累计数量]`
- 撮合引擎处理约 **140 万订单/秒**

**STP**：
- 支持 **6 种 STP 模式**：`NONE`、`EXPIRE_TAKER`、`EXPIRE_MAKER`、`EXPIRE_BOTH`、`DECREMENT`、`TRANSFER`
- **默认策略**：现货和期货默认均为 `EXPIRE_MAKER`（2023 年 10 月现货启用，2024 年 12 月期货强制启用）
- 但不同交易对可能配置不同默认值，通过 `GET /api/v3/exchangeInfo` 查询 `defaultSelfTradePreventionMode`
- 因 STP 过期的订单状态为 **`EXPIRED_IN_MATCH`**
- 支持 `tradeGroupId` 实现跨账户 STP
- STP 行为由 **taker order 的 STP mode** 决定（TRANSFER 例外，需双方均为 TRANSFER）

**余额模型**：
- `GET /api/v3/account` 返回 `balances` 数组，每个元素含 `asset`、`free`、`locked`
- 买单冻结 quote，卖单冻结 base
- 同一 quote 资产在所有交易对中共享资金池
- 支持**统一账户（Unified Account）**模式，跨币种共享保证金

**手续费**：
- 现货默认：Maker 0.1%，Taker 0.1%
- `GET /api/v3/account` 返回 `makerCommission` 和 `takerCommission`（单位为 0.01%）
- BNB 抵扣可享 25% 折扣
- `fills` 数组中返回每笔成交的 `commission` 和 `commissionAsset`

**订单类型**：
- 支持 `LIMIT`、`LIMIT_MAKER`、`MARKET`、`STOP_LOSS`、`STOP_LOSS_LIMIT`、`TAKE_PROFIT`、`TAKE_PROFIT_LIMIT`
- OCO 订单：限价单 + 止损限价单绑定，一个成交后另一个自动取消
- 合约支持 `TRAILING_STOP_MARKET`
- 现货不支持 Trailing Stop

**价格/数量限制**：
- `GET /api/v3/exchangeInfo` 的 `filters` 数组定义各交易对限制
- `PRICE_FILTER`：`minPrice`、`maxPrice`、`tickSize`
- `LOT_SIZE`：`minQty`、`maxQty`、`stepSize`
- `MIN_NOTIONAL` / `NOTIONAL`：`minNotional`、`maxNotional`
- `MAX_POSITION`：最大持仓限制
- `MARKET_LOT_SIZE`：市价单数量限制

### 10.2 OKX

**资源**：
- [OKX V5 API 官方文档](https://www.okx.com/docs-v5/en/)
- [OKX 统一账户解读](https://www.odaily.news/post/5192009)

**撮合引擎**：
- 价格优先 + 时间优先
- 单 taker 订单最多匹配 **1000 个** maker 订单，超出部分取消
- 每交易对最大挂单笔数：**500 笔**
- 全账户级别最大挂单笔数：**4,000 笔**

**STP**：
- 通过 `stpId` + `stpMode` 配置
- `stpMode`：`cancel_maker`、`cancel_taker`、`cancel_both`
- 同一用户（含主账户和子账户）之间的订单匹配视为自成交
- STP 在 FOK 订单中**不生效**

**余额模型**：
- 四种账户模式：Spot mode、Futures mode、Multi-currency margin、Portfolio margin
- 核心字段：`cashBal`（现金）、`eq`（权益）、`availBal`（可用）、`frozenBal`（冻结）、`ordFrozen`（订单冻结）
- 统一账户下，所有币种按 USD 折算共享保证金
- 支持**自动借币**：余额不足时自动借入

**手续费**：
- 现货：Maker 0.08%，Taker 0.10%
- 合约：Maker 0.02%，Taker 0.05%
- VIP 7+ maker 费率为**负值**（交易所返佣）
- OKB 折扣最高 40%

**订单类型**：
- 支持 `market`、`limit`、`post_only`、`fok`、`ioc`、`conditional`、`oco`、`move_order_stop`（跟踪止损）、`iceberg`、`twap`
- `limit` 默认等效于 GTC
- 现货和合约均支持 Trailing Stop

**价格/数量限制**：
- `GET /api/v5/account/instruments` 返回 `tickSz`、`lotSz`、`minSz`、`maxLmtSz`、`maxMktSz`
- 新上币 10 分钟后启用**限价价格保护规则**

### 10.3 Bybit

**资源**：
- [Bybit V5 API 文档（下单）](https://bybit-exchange.github.io/docs/v5/order/create-order)
- [Bybit V5 SMP 文档](https://bybit-exchange.github.io/docs/v5/smp)
- [Bybit V5 钱包余额](https://bybit-exchange.github.io/docs/v5/account/wallet-balance)
- [Bybit V5 手续费率](https://bybit-exchange.github.io/docs/v5/account/fee-rate)

**撮合引擎**：
- 价格-时间优先（FIFO），内存订单簿
- 单个合约支持高达 **100,000 TPS**
- Snapshot + Delta 的 WebSocket 数据分发模式

**STP（SMP）**：
- 功能名称：Self Match Prevention（SMP）
- 三种策略：`CancelMaker`、`CancelTaker`、`CancelBoth`
- 通过 `smpType` 参数在**下单时**指定
- 支持 **SMP Trade Group**：将多个 UID 编组，组内 UID 之间也受 SMP 保护
- 一旦订单入簿，其 `smpType` 即失效，后续匹配以新订单的 smpType 为准

**余额模型**：
- **Unified Trading Account（UTA）** 统一交易账户
- 核心字段：`walletBalance`、`locked`、`equity`、`totalOrderIM`、`totalPositionIM`、`totalAvailableBalance`
- 现货卖出冻结持仓，买入冻结计价货币
- 2025 年 9 月起钱包余额 API 新增 `spotBorrow` 字段

**手续费**：
- 现货：Maker 0.10%，Taker 0.10%
- USDT 永续：Maker 0.02%，Taker 0.055%
- `Transaction Log` 中 `fee` 为正表示支出，为负表示返佣

**订单类型**：
- 基础：`Limit`、`Market`
- TIF：`GTC`、`IOC`、`FOK`、`PostOnly`
- 高级：Conditional、TP/SL、OCO（Spot）、`reduceOnly`、`closeOnTrigger`
- 支持修改未成交或部分成交订单
- 现货近年已支持 Trailing Stop

**价格/数量限制**：
- `Get Instruments Info` 返回 `priceFilter` + `lotSizeFilter` + `riskParameters`
- `minNotionalValue`、`priceLimitRatioX` / `priceLimitRatioY`（价格涨跌幅限制）

### 10.4 Coinbase

**资源**：
- [Coinbase Advanced Trade API](https://coinbase-cloud.mintlify.app/coinbase-app/advanced-trade-apis/rest-api)
- [Coinbase Developer Docs 索引](https://docs.cloud.coinbase.com/llms.txt)

**撮合引擎**：
- 经典的**价格-时间优先**中心化限价订单簿（CLOB）
- 撮合延迟在**个位数微秒**，每秒处理 100,000+ 订单
- Public API 有 1 秒缓存，推荐用 WebSocket 获取实时数据

**STP**：
- 公开 API 文档中**未明确披露 STP 的具体策略配置**
- 从行业实践推断，Coinbase 在撮合层有内部自成交保护机制
- 机构级（Coinbase Prime）可能支持更精细的 STP 配置

**余额模型**：
- **分币种账户（Account-per-Currency）** 模型
- 核心字段：`available_balance`、`hold`
- 支持 **Portfolio** 功能：创建多个子组合，资金可在 Portfolio 之间划转
- 衍生品（FCM 期货）有独立的 `balance_summary` 和 `sweep` 机制

**手续费**：
- Advanced Trade 基础费率：**Maker 0.40%~0.60%，Taker 0.60%~1.20%**（显著高于 Binance/OKX/Bybit）
- 稳定币对：Maker 0.00%，Taker 0.10%~0.45%
- 最高层级（月交易量 $250M+）：Maker 0.00%，Taker 0.05%

**订单类型**：
- 使用强类型的 **order configuration** 对象：
  - `market_market_ioc`（现货市价单）
  - `limit_limit_gtc` / `limit_limit_gtd` / `limit_limit_fok`
  - `stop_limit_stop_limit_gtc` / `stop_limit_stop_limit_gtd`
  - `trigger_bracket_order_gtc` / `trigger_bracket_order_gtd`
- 支持 `post_only`、`reduce_only` 执行指令
- 支持 `preview_order` 在下单前模拟执行结果

**价格/数量限制**：
- `Get Product` 返回 `base_increment`（数量精度）、`quote_increment`（价格精度）、`base_min_size` / `base_max_size`

### 10.5 Kraken

**资源**：
- [Kraken REST API (Add Order)](https://docs.kraken.com/api/docs/rest-api/add-order)

**撮合引擎**：
- 价格-时间优先
- 支持 `deadline`（RFC3339 时间戳 + 60 秒内）：定义撮合引擎必须拒绝订单的时间点

**STP**：
- STP 参数：`stptype` = `cancel-newest`（默认）/ `cancel-oldest` / `cancel-both`
- 不支持跨账户/组 STP

**余额模型**：
- 经典 `free` / `locked` 模型
- 支持杠杆交易和保证金账户

**手续费**：
- 现货：Maker 0.16%，Taker 0.26%
- 交易量阶梯递减

**订单类型**：
- 支持条件平仓单（conditional close orders）
- 支持 `deadline` 参数定义订单有效期

### 10.6 传统交易所（Nasdaq/NYSE/CME）

**资源**：
- [Nasdaq STP Factsheet](https://www.nasdaq.com/docs/2024/04/02/Self-Trade-Prevention_Factsheet.pdf)
- [NYSE Pillar FIX Protocol Specification](https://www.nyse.com/publicdocs/nyse/NYSE_Pillar_Gateway_FIX_Protocol_Specification.pdf)
- [Euronext Optiq STP Functional Overview v2.0](https://connect2.euronext.com/sites/default/files/it-documentation/Self-Trade%20Prevention%20Functional%20Overview%20-%20v2.0.pdf)
- [CME Matching Algorithms](https://databento.com/blog/cme-matching-algorithms-explained)

**Nasdaq**：
- STP 默认策略：**Cancel Passive（等效于 Cancel Oldest / Expire Maker）**
- 支持三种粒度：MPID+Trader ID / MPID / Specified Trader Group
- 支持 **Create Technical Transfer**：将自成交转换为内部划转（类似 Binance 的 TRANSFER）

**NYSE Pillar**：
- FIX Tag 7928：`T`（None）、`N`（Cancel Newest）、`O`（Cancel Oldest）、`C`（Cancel Both）、`D`（Decrement）
- 支持 MPID-based 或 ClientID-based STP
- 支持 Session 级默认配置

**Euronext Optiq**：
- `Cancel Resting` / `Cancel Incoming` / `Cancel Both`
- 仅适用于连续交易阶段
- 支持 IMS（Internal Matching Service）兼容

**CME Globex**：
- 多种撮合算法并存：FIFO（占 70.3% 交易量）、Pro-Rata、Configurable、Allocation、Split 等
- FIFO 用于 ES、NQ、ZN、ZF、ZB、CL 等主流产品
- Pro-Rata 用于 6S、6M calendar spreads 等
- Configurable 算法结合 TOP、LMM、Split（FIFO+Pro-Rata）、Leveling 等步骤

---

## 11. 横向对比矩阵

### 11.1 核心机制对比

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
| **Trailing Stop 现货** | ❌ | ✅ | ✅ | ❓ | ❓ |
| **Trailing Stop 合约** | ✅ | ✅ | ✅ | ❓ | ❓ |

### 11.2 STP 策略对比

| 交易所 | 策略名称 | 策略数量 | 默认策略 | 订单级配置 | 跨账户/组支持 |
|--------|----------|----------|----------|------------|---------------|
| **Binance** | EXPIRE_TAKER / EXPIRE_MAKER / EXPIRE_BOTH / DECREMENT / TRANSFER / NONE | 6 | EXPIRE_MAKER（现货/期货） | ✅ `selfTradePreventionMode` | ✅ `tradeGroupId` |
| **OKX** | cancel_taker / cancel_maker / cancel_both | 3 | 未明确 | ✅ `stpId` + `stpMode` | ✅（主子账户间） |
| **Bybit** | CancelMaker / CancelTaker / CancelBoth | 3 | 未明确 | ✅ `smpType` | ✅ SMP Trade Group |
| **Coinbase** | 内部机制 | — | Cancel-Newest（推断） | ❌（未公开） | ❓ |
| **Kraken** | cancel-newest / cancel-oldest / cancel-both | 3 | cancel-newest | ✅ `stptype` | ❌ |
| **Nasdaq** | Cancel Passive / Cancel Aggressive / Cancel Both / Technical Transfer | 4 | Cancel Passive | ✅ | ✅ MPID/Trader Group |
| **NYSE Pillar** | T/N/O/C/D (FIX Tag 7928) | 5 | 可配置 | ✅ | ✅ MPID/ClientID |
| **Euronext** | Cancel Resting / Cancel Incoming / Cancel Both | 3 | 可配置 | ✅ | ❌ |

### 11.3 余额模型对比

| 维度 | Binance | OKX | Bybit | Coinbase |
|------|---------|-----|-------|----------|
| **账户模型** | 经典分离 / 统一账户（UA） | 统一交易账户（UTA） | 统一交易账户（UTA） | 分币种账户 + Portfolio |
| **可用余额字段** | `free` | `availBal` | `totalAvailableBalance` | `available_balance` |
| **冻结余额字段** | `locked` | `frozenBal` / `ordFrozen` | `locked` | `hold` |
| **权益字段** | `crossWalletBalance` | `eq` / `adjEq` | `equity` | — |
| **跨币种保证金** | ✅（统一账户） | ✅（多币种保证金模式） | ✅ | ❌ |
| **自动借币** | ❓ | ✅ | ❓ | ❌ |
| **保证金比率** | `marginRatio` | `mgnRatio` | — | — |

### 11.4 手续费对比（现货基础费率）

| 交易所 | Maker | Taker | 折扣机制 |
|--------|-------|-------|----------|
| **Binance** | 0.10% | 0.10% | BNB 抵扣 25% |
| **OKX** | 0.08% | 0.10% | OKB 折扣最高 40%，VIP7+ maker 负费率 |
| **Bybit** | 0.10% | 0.10% | — |
| **Coinbase** | 0.40%~0.60% | 0.60%~1.20% | 交易量阶梯递减 |
| **Kraken** | 0.16% | 0.26% | 交易量阶梯递减 |

---

## 12. 学术仿真与行业标准

### 12.1 开源仿真框架谱系

#### ABIDES 系列

**ABIDES**（Byrd, Hybinette & Balch, 2019）是当前最突出的开源高保真股票市场仿真器：

- **离散事件仿真（Discrete Event Simulation）**：时间分辨率达到**纳秒级**
- **消息协议**：参照 NASDAQ 的 **ITCH/OUCH** 协议设计
- **网络延迟模拟**：可配置 Agent 之间、Agent 与交易所之间的成对延迟
- **Background Agent**：通过"数据神谕"获取带噪声的历史交易观测，混合先验信念形成后验价值信念，从而复现特定历史交易日的价格走势

**ABIDES-Gym**（Amrouni et al., 2021）：
- 将 ABIDES 适配为基于 step 的 RL 训练框架
- 引入 `FinancialGymAgent` 作为单一可中断内核的 Agent
- **局限**：仅支持单个 RL Agent，移除了 ZI 等关键背景 Agent 类型

**ABIDES-MARL**（Cheridito, Dupret & Wu, 2025）：
- **核心创新**：解耦内核中断与状态收集，支持同步多智能体强化学习
- 引入 `StopSignalAgent` 协调所有 RL Agent，支持序贯或同时执行协议
- 恢复并扩展了 Kyle 模型中的渐进价格发现现象
- 在流动性交易者问题中，证明均衡执行策略会内生地塑造做市商行为和价格动态
- 支持与 LLM-based Agent 的混合范式（LLM 产生信号，MARL Agent 执行）

**ABIDES-Economist**（Dwarakanath et al., 2024）：
- 扩展 ABIDES 到宏观经济学仿真
- 包含家庭、企业、中央银行、政府等异质 Agent
- 支持 PPO 训练，用于探索政策反事实和涌现市场动态

#### PyMarketSim

**PyMarketSim**（Mascioli et al., 2024, ICAIF）：
- 基于 **4-Heap** 数据结构实现 LOB，$10^6$ 订单下平均操作时间 < 0.005ms
- 支持单 Agent 和 Multi-Agent RL 设置
- 引入 **TRON（Trained Response Order Network）Agent**：用 RNN 实现的自适应背景交易者
- 支持 **PSRO（Policy Space Response Oracles）** 进行均衡分析
- 吞吐量：300,000 LOB actions/秒 或 15,000 agent actions/秒
- **与 ABIDES 的对比**：PyMarketSim 更适合中等数量 Agent 的长期仿真；ABIDES 更适合大规模 Agent 的事件驱动仿真

#### JaxMARL-HFT

**JaxMARL-HFT**（2025, ACM ICAIF）：
- 基于 JAX-LOB 模拟器，实现 **GPU 加速**的大规模 MARL 训练
- 在单 GPU 上并行 4,000 环境，达到 351,119 steps/秒（单消息场景）
- 采用完全并发的经典 MARL 范式，可直接使用 JaxMARL 中的现有算法
- 与 ABIDES-gym 和 CPU-MARL 的对比显示显著速度优势

#### Zero-Intelligence (ZI) 交易者模型

**Gode & Sunder (1993)**：
- 即使交易者完全没有智能（随机出价），只要受到预算约束，市场配置效率也能接近 100%
- **启示**：市场微观结构（制度设计）本身对市场效率和价格发现起主导作用，这为 LOB 仿真提供了最简基线

#### Hawkes 过程模型

- 用于建模限价单、市价单和撤单到达时间的**相互激励**特性
- 市价单执行后，限价单更可能快速到达以"补充"被消耗的流动性
- 能够复现波动率聚集（volatility clustering）等关键微观结构特征

### 12.2 FIX 协议标准

FIX 协议是金融信息交换的国际标准，对 STP 有明确定义：

- **Tag 7928: SelfTradeType**（NYSE Pillar 采用）
  - `T` = No Self Trade Prevention
  - `N` = Cancel Newest
  - `O` = Cancel Oldest
  - `C` = Cancel Both
  - `D` = Cancel Decrement
- **Tag 2362: SelfMatchPreventionID**：可选的 STP ID，用于分组隔离

> 行业趋势：Cancel Oldest（即 Expire Maker / Cancel Passive）是最常见的默认策略，因为 resting order 已"承诺"提供流动性，incoming order 是"新"的。

### 12.3 传统交易所 vs 数字货币交易所

| 维度 | 传统交易所（Nasdaq/NYSE/CME） | 数字货币交易所 |
|------|--------------------------|---------------|
| **交易时间** | 固定时段（如 9:30-16:00 ET），有开盘/收盘集合竞价 | 7×24 小时连续交易 |
| **撮合算法** | 以 Price-Time Priority 为主；部分期权/期货支持 Pro-Rata、Configurable、Allocation 等 | 绝大多数采用 Price-Time Priority |
| **延迟要求** | 纳秒级竞争，共置（co-location）是重要优势 | 毫秒级已足够优秀 |
| **订单类型** | Market, Limit, Stop, IOC, FOK, GTC, Iceberg, ALO | 更丰富：Post-Only, Reduce-Only, OCO, Trailing Stop, 杠杆订单 |
| **STP 默认行为** | 通常默认启用或需显式配置 | 多数默认启用 STP |
| **最小价格单位** | 严格监管定义，按资产价格分级 | 由交易所自行设定，通常较小 |
| **结算与清算** | T+2 / T+1 集中清算（DTCC 等） | 实时或准实时结算 |
| **监管与合规** | 严格（SEC, FINRA, MiFID II）；有熔断机制、涨跌停限制 | 相对宽松；部分有价格保护机制 |
| **流动性结构** | 做市商义务、DMM（指定做市商）、Retail Priority 等复杂层级 | 主要靠用户自发流动性 + maker-taker 费率激励 |
| **市场数据协议** | ITCH, OUCH, FIX 5.0, SBE | REST/WebSocket API, 部分支持 FIX |

---

## 13. 完整功能全景与实现优先级建议

### 13.1 功能全景分类

以下按交易机制的内在逻辑层次，列出交易所仿真环境可能实现的全部功能。

#### L1：核心基础设施（所有交易所共用）

| 功能 | 说明 |
|------|------|
| 限价订单簿（LOB） | 维护 bids/asks 队列，支持价格优先时间优先 |
| 撮合引擎（FIFO） | 价格优先时间优先匹配算法 |
| 基础限价单（LIMIT） | 以指定价格挂簿，未成交部分等待 |
| 市价单（MARKET） | 立即以最优价成交 |
| 订单状态机 | NEW / PARTIALLY_FILLED / FILLED / CANCELED / EXPIRED / REJECTED |
| GTC 时间策略 | 一直有效直到取消或完全成交 |
| 资金冻结 | 下单时冻结对应资产 |
| 跨交易对资金共享 | 同一资产在多交易对间共享资金池 |
| 手续费结算（Maker-Taker） | received-asset 扣除模式 |
| Filter 校验 | tickSize / stepSize / minNotional / priceRange / qtyRange |

#### L2：现货增强功能

| 功能 | 说明 |
|------|------|
| IOC 时间策略 | 立即成交可成交部分，剩余取消 |
| FOK 时间策略 | 必须完全成交，否则全部取消 |
| Post-Only 指令 | 仅作为 maker 挂单，若会立即成交则拒绝 |
| STP 自成交保护 | 防止同一实体自买自卖 |
| 订单修改（Amend） | 修改数量/价格（可能保持/不保持时间优先权） |
| 订单取消 | 用户主动取消未成交订单 |
| 价格保护 | 价格涨跌幅限制、市价单数量限制 |
| 订单簿快照 API | 返回前 n 档聚合深度 |

#### L3：条件订单

| 功能 | 说明 |
|------|------|
| Stop-Market | 触发后转为市价单 |
| Stop-Limit | 触发后转为限价单 |
| Take-Profit Market | 止盈市价单 |
| Take-Profit Limit | 止盈限价单 |
| 价格触发源 | Last Price / Mark Price / Index Price |
| 条件单引擎 | 维护未触发条件单列表，每 tick 检查触发条件 |

#### L4：组合订单

| 功能 | 说明 |
|------|------|
| OCO 订单 | 两单绑定，一单位成交则另一单自动取消 |
| 冰山订单 | 只暴露部分数量，隐藏部分自动补充 |
| Trailing Stop | 动态调整触发价的跟踪止损 |

#### L5：杠杆与保证金

| 功能 | 说明 |
|------|------|
| 逐仓杠杆（Isolated Margin） | 独立保证金池 |
| 全仓杠杆（Cross Margin） | 统一保证金池，盈亏互抵 |
| 自动借币 | 余额不足时自动借入 |
| 借贷利息 | 按小时计息 |
| 初始保证金计算 | IM = 名义价值 / 杠杆 |
| 维持保证金计算 | MM = 名义价值 × 维持保证金率 |
| 保证金比率监控 | 实时计算 margin ratio |
| 强平引擎 | 触发条件、市价平仓 |

#### L6：永续合约

| 功能 | 说明 |
|------|------|
| 资金费率计算 | Premium Index + Clamp(Interest Rate - Premium, 上限, 下限) |
| 资金费结算 | 每 8 小时（或更短）多空支付 |
| 标记价格 | Median(Index, Index+MA, Contract Price) |
| 指数价格 | 多交易所加权平均 |
| 未实现盈亏（UPnL） | 基于 Mark Price 计算 |
| 保险基金 | 弥补穿仓损失 |
| ADL（自动减仓） | 盈利高杠杆用户优先被平仓 |

#### L7：交割期货

| 功能 | 说明 |
|------|------|
| 合约生命周期管理 | 创建、交易、到期 |
| 到期结算 | 以交割价格现金结算 |
| 基差收敛 | 期货价格向现货收敛 |

#### L8：期权

| 功能 | 说明 |
|------|------|
| 期权定价引擎 | Black-Scholes-Merton |
| Greeks 计算 | Delta / Gamma / Theta / Vega |
| 合约生命周期 | 创建、交易、到期行权 |
| 到期行权处理 | 实值自动行权，现金结算 |
| 组合保证金 | 考虑 Delta 中性等对冲效应 |

### 13.2 优先级排序

以下优先级基于**实现难度**和**对仿真环境的增强价值**综合评估，覆盖从核心基础设施到期权合约的完整功能谱系。

| 优先级 | 功能 | 实现难度 | 价值 | 关键新增状态/模块 |
|--------|------|----------|------|-----------------|
| **P0** | 限价订单簿 + FIFO 撮合 | ⭐ 低 | 必需 | 订单簿核心数据结构 |
| **P0** | 资金冻结（free/locked） | ⭐ 低 | 必需 | 余额状态 |
| **P0** | 手续费结算（Maker-Taker） | ⭐ 低 | 必需 | 费率配置 |
| **P0** | Filter 校验 | ⭐ 低 | 必需 | 交易对参数 |
| **P0** | 订单状态机（NEW/FILLED/CANCELED） | ⭐ 低 | 必需 | 订单状态字段 |
| **P1** | 市价单 | ⭐ 低 | 高 | 订单簿遍历撮合逻辑 |
| **P1** | IOC / FOK | ⭐⭐ 中低 | 高 | `time_in_force` 字段 + 撮合后剩余量处理 |
| **P1** | Post-Only | ⭐ 低 | 中高 | 订单属性 + 成交预判 |
| **P1** | STP 可配置化 | ⭐⭐ 中低 | 高 | STP 策略枚举 + 撮合循环处理 |
| **P1** | Stop-Market / TP-Market | ⭐⭐ 中低 | 高 | 条件单引擎 + 未触发订单列表 |
| **P2** | Stop-Limit / TP-Limit | ⭐⭐⭐ 中 | 高 | 母单→子单映射关系 |
| **P2** | OCO 订单 | ⭐⭐⭐ 中 | 中 | `OrderGroup` + 成交事件监听器 |
| **P2** | 订单修改（Amend） | ⭐⭐ 中低 | 中 | 订单更新 + 时间优先保持 |
| **P2** | 价格保护机制 | ⭐⭐ 中低 | 中 | 涨跌幅限制 + 市价单上限 |
| **P3** | Trailing Stop | ⭐⭐⭐⭐ 中高 | 中 | 动态触发价状态 + 峰值价格追踪 |
| **P3** | 冰山订单 | ⭐⭐⭐ 中 | 低 | 暴露/隐藏数量管理 |
| **P3** | 杠杆（逐仓） | ⭐⭐⭐⭐ 中高 | 高 | 仓位层状态 + 保证金计算模块 |
| **P4** | 永续合约 | ⭐⭐⭐⭐⭐ 高 | 高 | Funding Rate、Mark Price、Insurance Fund、ADL |
| **P4** | 全仓杠杆 | ⭐⭐⭐⭐⭐ 高 | 中 | 跨仓位保证金共享 + 连锁强平 |
| **P5** | 交割期货 | ⭐⭐⭐⭐ 中高 | 中 | 合约生命周期管理 + 到期结算引擎 |
| **P5** | 期权 | ⭐⭐⭐⭐⭐ 高 | 低（当前阶段）| BSM 定价引擎 + Greeks 计算 + 行权处理器 |

**排序逻辑说明**：

- **P0（基础设施）**：任何可运行的仿真环境必须包含的核心机制
- **P1（现货增强）**：显著提升仿真真实性和策略表达能力的现货层功能
- **P2（高级订单）**：支持更复杂交易策略的条件单和组合单
- **P3（特殊订单+杠杆入门）**：跟踪止损、冰山订单属于特殊场景；逐仓杠杆是衍生品仿真的前置条件
- **P4（衍生品核心）**：永续合约是数字货币市场交易量最大的产品；全仓杠杆是永续的配套机制
- **P5（完整生态）**：交割期货和期权属于更完整的金融市场生态，当前阶段价值相对较低

### 13.3 对 TradeMasterOnline 的设计建议

基于以上调研，针对 TradeMasterOnline 交易仿真环境的设计，提出以下具体建议：

#### 建议 1：STP 默认策略可配置化

**问题**：STP 默认策略在不同交易所间存在差异（Binance 默认 EXPIRE_MAKER，Kraken 默认 cancel-newest，Nasdaq 默认 Cancel Passive），且 Binance 不同交易对的默认值可能不同。

**建议**：
- 在 `config.yaml` 中增加 `default_stp_mode` 字段，支持 `"expire_maker"`（默认）、`"expire_taker"`、`"expire_both"`、`"none"`
- 在 `Order` 模型中增加可选的 `stp_mode` 字段，允许单笔订单覆盖默认策略
- 在 `Matcher.match()` 的撮合循环中，按配置的 STP 策略（expire_maker / expire_taker / expire_both / none）处理自成交事件

#### 建议 2：手续费精度处理

**问题**：手续费按 `qty * (1 - fee)` 计算，可能存在浮点误差累积。

**建议**：
- 参考 Binance 的 `baseCommissionPrecision` 和 `quoteCommissionPrecision`，在结算中对手续费金额进行精度截断
- 在 `config.yaml` 的 `fees` 下增加 `base_precision`、`quote_precision` 字段（或使用 Python `decimal.Decimal`）

#### 建议 3：订单状态流转明确化

建议明确以下状态流转：

```
NEW → PARTIALLY_FILLED → FILLED
 ↓
CANCELED (by user / by OCO trigger / by system)
 ↓
EXPIRED (IOC/FOK rules, STP triggered, deadline reached)
 ↓
REJECTED (filter failure, insufficient balance)
```

#### 建议 4：分层架构设计

建议将系统分为三层：

| 层次 | 职责 |
|------|------|
| **订单层** | 订单创建、修改、取消、条件单触发 |
| **撮合层** | 订单簿维护、撮合匹配、STP 处理 |
| **结算层** | 余额冻结/释放、手续费扣除、持仓更新 |

#### 建议 5：引入学术基准

- **Zero-Intelligence 交易者**：作为最简基线，验证市场微观结构设计的正确性
- **固定 PRNG 种子**：确保实验可重复，支持 A/B 测试
- **完整订单流日志**：记录完整订单流，支持 price impact 分析

#### 建议 6：建议的 config.yaml 扩展

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

---

## 14. 参考资料

### 交易所官方文档

1. Binance Spot REST API Docs: https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md
2. Binance STP FAQ: https://github.com/binance/binance-spot-api-docs/blob/master/faqs/stp_faq.md
3. Binance ENUM Definitions: https://github.com/binance/binance-spot-api-docs/blob/master/enums.md
4. Binance Order Amend Keep Priority: https://github.com/binance/binance-spot-api-docs/blob/master/faqs/order_amend_keep_priority.md
5. Binance Trailing Stop FAQ: https://github.com/binance/binance-spot-api-docs/blob/master/faqs/trailing-stop-faq.md
6. OKX V5 API Docs: https://www.okx.com/docs-v5/en/
7. Bybit V5 API Docs: https://bybit-exchange.github.io/docs/v5/order/create-order
8. Bybit V5 SMP Docs: https://bybit-exchange.github.io/docs/v5/smp
9. Coinbase Advanced Trade API: https://coinbase-cloud.mintlify.app/coinbase-app/advanced-trade-apis/rest-api
10. Kraken REST API Docs: https://docs.kraken.com/api/docs/rest-api/add-order

### 传统交易所文档

11. Nasdaq STP Factsheet: https://www.nasdaq.com/docs/2024/04/02/Self-Trade-Prevention_Factsheet.pdf
12. NYSE Pillar FIX Protocol Specification: https://www.nyse.com/publicdocs/nyse/NYSE_Pillar_Gateway_FIX_Protocol_Specification.pdf
13. Euronext Optiq STP Functional Overview v2.0: https://connect2.euronext.com/sites/default/files/it-documentation/Self-Trade%20Prevention%20Functional%20Overview%20-%20v2.0.pdf
14. Nasdaq Equity Trading Rules: https://listingcenter.nasdaq.com/rulebook/nasdaq/rules/Nasdaq%20Equity%204
15. CME Matching Algorithms Explained: https://databento.com/blog/cme-matching-algorithms-explained

### 学术文献

16. ABIDES: Towards High-Fidelity Market Simulation for AI Research (arXiv:1904.12066): https://ar5iv.labs.arxiv.org/html/1904.12066
17. ABIDES-MARL: Multi-Agent RL for LOB Simulation (arXiv:2511.02016): https://arxiv.org/abs/2511.02016
18. ABIDES-Gym / RL Execution in ABIDES (arXiv:2006.05574): https://arxiv.org/abs/2006.05574
19. ABIDES-Economist: Multi-Agent Macroeconomic Simulator (Dwarakanath et al., 2024)
20. JaxMARL-HFT: GPU-Accelerated Large-Scale MARL for HFT (ACM ICAIF 2025): https://dl.acm.org/doi/10.1145/3768292.3770416
21. PyMarketSim: A Financial Market Simulation Environment for Trading Agents Using Deep RL (ACM ICAIF 2024): https://doi.org/10.1145/3677052.3698639
22. Limit Order Book Simulations: A Review (arXiv:2402.17359): https://arxiv.org/html/2402.17359v1
23. MAXE: Fast Agent-Based LOB Simulation (arXiv:2008.07871): https://arxiv.org/abs/2008.07871
24. Gode & Sunder (1993) Zero-Intelligence Traders, JPE 101(1):119-137
25. Kyle (1985) Continuous Auctions and Insider Trading, Econometrica 53:1315-1335
26. Cont, Stoikov & Talreja (2010) Stochastic Model for Order Book Dynamics, Operations Research 58(3)

### 开源项目

27. ABIDES GitHub: https://github.com/abides-sim/abides
28. PyMarketSim GitHub: https://github.com/umichsrg/pymarketsim
29. JaxMARL-HFT GitHub: https://github.com/vmohl/JaxMARL-HFT

### 行业报告与新闻

30. Binance to extend Self-Trade Prevention to all Futures users (2024-11-25): https://fxnewsgroup.com/forex-news/cryptocurrency/binance-to-extend-self-trade-prevention-function-to-all-binance-futures-users/
31. Binance Launches STP Feature for Spot and Margin Trading (2023-10-11): https://www.coinspeaker.com/binance-self-trade-spot-margin/
