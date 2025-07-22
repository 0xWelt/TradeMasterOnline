# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TradeMasterOnline is a multiplayer online trading simulation game built with Python 3.12+ using a vibe coding approach. It provides a simulated cryptocurrency exchange with support for BTC/USDT trading pairs, order matching, price updates, and comprehensive visualization capabilities.

## Core Architecture

### Main Components

**Exchange Engine (`tmo/exchange.py`)**
- `Exchange` class: Central trading engine managing orders, trades, and market data
- Order matching system using price-time priority
- Real-time price updates based on executed trades
- Order book management with buy/sell order sorting
- Trade history and order lifecycle management

**Data Models (`tmo/typing.py`)**
- `Asset`/`AssetType`: Asset definitions (USDT, BTC)
- `Order`/`OrderType`: Order management with validation and lifecycle states
- `Trade`: Transaction records linking buy/sell orders
- `TradingPair`: Market data including current price and last update

**Visualization (`tmo/visualization.py`)**
- `ExchangeVisualizer`: Interactive timeline and chart generation
- Real-time state snapshots with step-by-step progression
- Plotly-based interactive charts with HTML export
- Multi-panel visualization including price trends, order book depth, and user activity

## Development Commands

### Environment Setup
```bash
# Install dependencies
uv sync

# Run development environment
uv run python examples/exchange_demo.py
```

### Testing
```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=tmo --cov-report=html --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_exchange.py

# Run single test
uv run pytest tests/test_exchange.py::test_order_matching
```

### Code Quality
```bash
# Format code
uv run ruff format

# Check code style and fix issues
uv run ruff check --fix

# Run pre-commit hooks
uv run pre-commit run --all-files
```

### Running Examples
```bash
# Interactive trading demo with visualization
uv run python examples/exchange_demo.py

# This generates examples/exchange_demo.html with interactive charts
```

## Key Usage Patterns

### Basic Exchange Usage
```python
from tmo import Exchange, AssetType, OrderType

exchange = Exchange()

# Place orders
buy_order = exchange.place_order(
    user_id='user1',
    order_type=OrderType.BUY,
    asset=AssetType.BTC,
    quantity=1.0,
    price=50000.0
)

# Get market data
btc_pair = exchange.get_trading_pair(AssetType.BTC)
order_book = exchange.get_order_book(AssetType.BTC)
trades = exchange.get_recent_trades(AssetType.BTC)
```

### Visualization Workflow
```python
from tmo import ExchangeVisualizer

visualizer = ExchangeVisualizer()
visualizer.record_snapshot(exchange, 'initial_state')
# ... perform trading operations ...
visualizer.create_visualization(exchange, 'output.html')
```

## Code Standards

### Language & Formatting
- Python 3.12+ with full type annotations
- Chinese comments and documentation supported
- 100 character line limit
- Single quotes for strings, double for docstrings
- No relative imports (absolute imports only)

### Dependencies
- `pydantic`: Data validation and models
- `loguru`: Structured logging
- `plotly`: Interactive visualization
- `pandas`: Data manipulation
- `matplotlib`: Static plotting support

### Testing Requirements
- All tests must pass (`uv run pytest`)
- Coverage >80% recommended
- Test files: `tests/test_*.py`
- Use descriptive test names in Chinese or English
- Include both normal and edge case testing

### Pre-commit Configuration
- `ruff`: Code formatting and linting
- `codespell`: Spelling checks
- Format on save recommended

## Project Structure

```
TradeMasterOnline/
├── tmo/                    # Main package
│   ├── exchange.py        # Trading engine
│   ├── typing.py          # Data models and types
│   └── visualization.py   # Chart generation
├── examples/              # Usage examples
│   └── exchange_demo.py   # Complete demo with visualization
├── tests/                 # Test suite
├── docs/                  # Documentation
└── pyproject.toml         # Project configuration
```

## Common Development Tasks

1. **Add new trading features**: Extend `Exchange` class in `exchange.py`
2. **Modify data models**: Update types in `typing.py` with proper validation
3. **Enhance visualization**: Extend `ExchangeVisualizer` with new chart types
4. **Add tests**: Create test files in `tests/` following existing patterns
5. **Run demos**: Use `examples/exchange_demo.py` for testing changes
