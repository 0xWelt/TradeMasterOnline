# TradeMasterOnline

[![CI](https://github.com/0xWelt/TradeMasterOnline/workflows/Pytest/badge.svg)](https://github.com/0xWelt/TradeMasterOnline/actions)
[![codecov](https://codecov.io/gh/0xWelt/TradeMasterOnline/branch/main/graph/badge.svg?token=codecov-umbrella)](https://codecov.io/gh/0xWelt/TradeMasterOnline)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/0xWelt/TradeMasterOnline/blob/main/LICENSE)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

A multi-agent trading simulation game.

## 🚀 Quick Start

### Requirements

- Python 3.14
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

```bash
git clone https://github.com/0xWelt/TradeMasterOnline.git
cd TradeMasterOnline
uv sync --extra dev
```

### Run Tests

```bash
uv run pytest
```

## 📋 Features

- **Multi-Agent Trading Simulation**: Simulate multiple autonomous agents trading in a virtual exchange.
- **Order Matching Engine**: Price-time priority matching for limit and market orders.
- **Real-Time Price Discovery**: Dynamic price updates based on executed trades.
- **Interactive Visualization**: Plotly-based charts for price history and order book analysis.
- **Type Safety**: Full type annotations with Pydantic.
- **Modern Tooling**: Python 3.14, uv, ruff, and Astral's `ty` type checker.

## 🏗️ Project Structure

```
TradeMasterOnline/
├── tmo/                    # Main package (core trading engine)
├── examples/               # Usage examples and simulations
├── tests/                  # Test suite
├── .github/workflows/      # CI/CD (Lint + Pytest)
├── docs/                   # Documentation
├── pyproject.toml          # Project configuration
└── README.md               # This file
```

## 🛠️ Development

### Setup

```bash
# Install dependencies
uv sync --extra dev

# Install pre-commit hooks
uv run pre-commit install
```

### Commands

| Command | Description |
|---------|-------------|
| `uv run pytest` | Run all tests |
| `uv run pytest --cov` | Run tests with coverage |
| `uv run ruff format` | Format code |
| `uv run ruff check --fix` | Fix linting issues |
| `uv run pre-commit run --all-files` | Run all pre-commit hooks |

## 📄 License

Distributed under the Apache-2.0 License. See [`LICENSE`](./LICENSE) for details.

## 🤝 Acknowledgments

- Built with [uv](https://github.com/astral-sh/uv) — Python package manager
- Code style by [ruff](https://github.com/astral-sh/ruff) — Fast Python linter
- Type checking by [ty](https://github.com/astral-sh/ty) — Astral's type checker
- Testing with [pytest](https://pytest.org/) and [pytest-cov](https://pytest-cov.readthedocs.io/)
- Data validation with [pydantic](https://docs.pydantic.dev/)
- Visualization with [plotly](https://plotly.com/python/)
