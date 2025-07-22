# TradeMasterOnline

[![CI](https://github.com/0xWelt/TradeMasterOnline/workflows/Pytest%20CI/badge.svg)](https://github.com/0xWelt/TradeMasterOnline/actions)
[![codecov](https://codecov.io/gh/0xWelt/TradeMasterOnline/branch/main/graph/badge.svg?token=codecov-umbrella)](https://codecov.io/gh/0xWelt/TradeMasterOnline)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/0xWelt/TradeMasterOnline/blob/main/LICENSE)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

A multi-agent trading simulation game built almost entirely with vibe coding with K2.

## 🚀 Quick Start

### Installation
```bash
# Clone the repository
git clone https://github.com/0xWelt/TradeMasterOnline.git
cd TradeMasterOnline

# Install dependencies
uv sync --extra dev
```

### Basic Usage
```python
from tmo import Exchange, AssetType, OrderType

exchange = Exchange()

# Place a buy order
order = exchange.place_order(
    user_id='user1',
    order_type=OrderType.BUY,
    asset=AssetType.BTC,
    quantity=1.0,
    price=50000.0
)

# Get market data
btc_pair = exchange.get_trading_pair(AssetType.BTC)
print(f"BTC/USDT: ${btc_pair.current_price:,.2f}")
```

### Run Tests
```bash
uv run pytest --cov=tmo --cov-report=html --cov-report=term-missing
```

## 📋 Features

### Core Trading Features
- **Asset Support**: USDT and BTC assets
- **Trading Pairs**: BTC/USDT with real-time price updates
- **Order System**: Buy/Sell orders with automatic matching
- **Order Book**: Price-sorted matching engine
- **Trade History**: Complete transaction records

### Technical Features
- **Type Safety**: Full type annotations with Pydantic
- **Modern Stack**: Python 3.12+ with uv package management
- **Code Quality**: Ruff formatting and pre-commit hooks
- **Testing**: Comprehensive pytest suite with coverage
- **Documentation**: Chinese and English support

## 🏗️ Architecture

### Core Components

**Exchange Engine (`tmo/exchange.py`)**
- Central trading engine managing orders and trades
- Order matching system using price-time priority
- Real-time price updates based on executed trades

**Data Models (`tmo/typing.py`)**
- `AssetType`: USDT, BTC asset definitions
- `Order`: Order management with lifecycle states
- `Trade`: Transaction records between buy/sell orders
- `TradingPair`: Market data and price tracking

## 🛠️ Development

### Environment Setup
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --extra dev

# Run tests
uv run pytest

# Format code
uv run ruff format

# Check code style
uv run ruff check
```

### Development Commands
| Command | Description |
|---------|-------------|
| `uv run pytest` | Run all tests |
| `uv run pytest --cov` | Run tests with coverage |
| `uv run ruff format` | Format code |
| `uv run ruff check --fix` | Fix linting issues |
| `uv run pre-commit run --all-files` | Run pre-commit hooks |

## 📊 Testing and Coverage

## 🏗️ Project Structure

```
TradeMasterOnline/
├── tmo/                    # Main package
│   ├── __init__.py        # Package exports
│   ├── exchange.py        # Trading engine
│   └── typing.py          # Data models
├── tests/                 # Test suite
├── .github/               # GitHub Actions
├── docs/                  # Documentation
├── pyproject.toml         # Project configuration
└── README.md             # Project documentation
```

## 🚀 Installation

### Requirements
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager

### From Source
```bash
git clone https://github.com/0xWelt/TradeMasterOnline.git
cd TradeMasterOnline
uv sync --extra dev
```

## 🎯 Usage Examples

### Basic Trading
```python
from tmo import Exchange, AssetType, OrderType

exchange = Exchange()

# Create buy order
buy_order = exchange.place_order(
    user_id='alice',
    order_type=OrderType.BUY,
    asset=AssetType.BTC,
    quantity=1.0,
    price=50000.0
)

# Create sell order
sell_order = exchange.place_order(
    user_id='bob',
    order_type=OrderType.SELL,
    asset=AssetType.BTC,
    quantity=0.5,
    price=50000.0
)

# View trades
trades = exchange.get_recent_trades(AssetType.BTC)
for trade in trades:
    print(f"Trade: {trade.quantity} BTC @ ${trade.price:,.2f}")
```

### Advanced Features
```python
# Get order book
order_book = exchange.get_order_book(AssetType.BTC)
print(f"Top buy: ${order_book[OrderType.BUY][0].price}")
print(f"Top sell: ${order_book[OrderType.SELL][0].price}")

# Cancel order
exchange.cancel_order(order_id)
```

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=0xWelt/TradeMasterOnline&type=Date)](https://star-history.com/#0xWelt/TradeMasterOnline&Date)

## 👥 Contributors

<a href="https://github.com/0xWelt/TradeMasterOnline/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=0xWelt/TradeMasterOnline" alt="Contributors" />
</a>

## 📜 Citation

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
- Code style by [ruff](https://github.com/astral-sh/ruff) - Fast Python linter
- Testing with [pytest](https://pytest.org/) and [pytest-cov](https://pytest-cov.readthedocs.io/)
- Data validation with [pydantic](https://docs.pydantic.dev/)
- Visualization with [plotly](https://plotly.com/python/)

<br/>

<div align="right">
  <a href="#top">🔝 back to top</a>
</div>
