# TradeMasterOnline

[![CI](https://github.com/0xWelt/TradeMasterOnline/workflows/Pytest%20CI/badge.svg)](https://github.com/0xWelt/TradeMasterOnline/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/0xWelt/TradeMasterOnline/blob/main/LICENSE)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

A multi-agent trading simulation game built almost entirely with vibe coding with K2.

## 项目概述

TradeMasterOnline 是一个使用 Python 3.12+ 构建的多智能体交易模拟游戏，采用vibe coding方法开发。该项目提供了一个模拟的加密货币交易所，支持BTC/USDT交易对的完整交易功能。

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
uv run python examples/exchange_demo.py
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
│   ├── typing.py          # 类型定义和数据模型
│   └── exchange.py        # 交易所核心逻辑
├── examples/              # 示例代码目录
│   └── __init__.py
├── tests/                 # 测试目录
│   ├── __init__.py
│   ├── test_typing.py     # 类型定义测试
│   └── test_exchange.py   # 交易所测试
├── docs/                  # 文档目录
├── pyproject.toml         # 项目配置
└── README.md             # 项目说明
```

## 核心组件

### 类型定义 (`tmo.typing`)
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
from tmo.typing import AssetType, OrderType

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
for trade in trades:
    print(f"成交: {trade.quantity} BTC @ ${trade.price:,.2f}")

# 查看当前价格
btc_pair = exchange.get_trading_pair(AssetType.BTC)
print(f"BTC/USDT 价格: ${btc_pair.current_price:,.2f}")
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

## 📊 Testing and Coverage

[![pytest](https://img.shields.io/badge/pytest-8.4.1-brightgreen.svg)](https://pytest.org/)
[![coverage](https://img.shields.io/badge/coverage-97%25-brightgreen.svg)](https://github.com/0xWelt/TradeMasterOnline/actions)

所有测试通过，代码覆盖率97%。运行测试：
```bash
uv run pytest --cov=tmo --cov-report=html --cov-report=term-missing
```

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=0xWelt/TradeMasterOnline&type=Date)](https://star-history.com/#0xWelt/TradeMasterOnline&Date)

## 👥 Contributors

<a href="https://github.com/0xWelt/TradeMasterOnline/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=0xWelt/TradeMasterOnline" alt="Contributors" />
</a>

感谢所有贡献者！欢迎通过Issue和PR参与项目。

## 📜 Citation

如果你在你的研究或项目中使用了TradeMasterOnline，请引用：

```bibtex
@software{TradeMasterOnline,
  author  = {0xWelt},
  title   = {TradeMasterOnline: A multi-agent trading simulation game built with vibe coding},
  url     = {https://github.com/0xWelt/TradeMasterOnline},
  license = {Apache-2.0},
  year    = {2025}
}
```

## 📄 License

Distributed under the Apache-2.0 License. See [`LICENSE`](./LICENSE) for details.

## 🤝 Acknowledgments

- Built with [uv](https://github.com/astral-sh/uv) - Python package manager
- Code style by [ruff](https://github.com/astral-sh/ruff) - Fast Python linter and formatter
- Testing with [pytest](https://pytest.org/) and [pytest-cov](https://pytest-cov.readthedocs.io/)
- Data validation with [pydantic](https://docs.pydantic.dev/)
- Visualization with [plotly](https://plotly.com/python/)

<br/>

<div align="right">
  <a href="#top">🔝 back to top</a>
</div>
