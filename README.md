# TradeMasterOnline

多人在线交易模拟游戏，使用 vibe coding 构建。

## 项目概述

TradeMasterOnline 是一个模拟交易所系统，实现了基础的交易功能，包括订单匹配、价格更新和交易记录等核心特性。

## 功能特性

### 核心功能
- **资产支持**：支持 USDT 和 BTC 两种资产
- **交易对**：提供 BTC/USDT 交易对
- **订单系统**：支持买入和卖出订单
- **订单匹配**：自动匹配可成交的订单
- **价格更新**：根据成交情况实时更新价格
- **订单簿管理**：维护按价格排序的订单簿

### 技术特性
- **类型安全**：使用 Pydantic 进行数据验证
- **代码质量**：遵循严格的编码规范
- **完整测试**：提供全面的单元测试
- **文档完善**：详细的代码文档和示例

## 快速开始

### 环境要求
- Python 3.12+
- uv 包管理器

### 安装依赖
```bash
uv sync
```

### 运行示例
```bash
uv run python -m tmo.example
```

### 运行测试
```bash
uv run pytest
```

### 检查代码质量
```bash
uv run pre-commit run --all-files
```

## 项目结构

```
TradeMasterOnline/
├── tmo/                    # 主要代码目录
│   ├── __init__.py        # 包初始化
│   ├── models.py          # 数据模型
│   ├── exchange.py        # 交易所核心逻辑
│   └── example.py         # 使用示例
├── tests/                 # 测试目录
│   ├── __init__.py
│   ├── test_models.py     # 数据模型测试
│   └── test_exchange.py   # 交易所测试
├── docs/                  # 文档目录
├── pyproject.toml         # 项目配置
└── README.md             # 项目说明
```

## 核心组件

### 数据模型 (`tmo.models`)
- `AssetType`：资产类型枚举
- `OrderType`：订单类型枚举
- `Asset`：资产模型
- `Order`：订单模型
- `Trade`：成交记录模型
- `TradingPair`：交易对模型

### 交易所 (`tmo.exchange`)
- `Exchange`：交易所核心类
  - 订单管理
  - 订单匹配
  - 价格更新
  - 订单簿维护

## 使用示例

```python
from tmo.exchange import Exchange
from tmo.models import AssetType, OrderType

# 创建交易所实例
exchange = Exchange()

# 下买单
buy_order = exchange.place_order(
    user_id='user1',
    order_type=OrderType.BUY,
    asset=AssetType.BTC,
    quantity=1.0,
    price=50000.0
)

# 下卖单
sell_order = exchange.place_order(
    user_id='user2',
    order_type=OrderType.SELL,
    asset=AssetType.BTC,
    quantity=0.5,
    price=50000.0
)

# 查看成交记录
trades = exchange.get_recent_trades(AssetType.BTC)

# 查看当前价格
btc_pair = exchange.get_trading_pair(AssetType.BTC)
print(f'BTC/USDT 价格: ${btc_pair.current_price:,.2f}')
```

## 开发规范

### 代码质量
- 使用 ruff 进行代码格式化和检查
- 遵循 flake8 规范
- 使用类型注解
- 支持中文注释和文档

### 测试要求
- 所有新功能必须提供单元测试
- 测试覆盖度建议 >80%
- 使用 pytest 框架

### 提交规范
- 使用 pre-commit 进行代码质量检查
- 编写清晰的提交信息
- 确保所有测试通过

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

- 项目团队：TradeMasterOnline Team
- 邮箱：team@trademaster.online
