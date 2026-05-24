"""测试 examples/random_agents.py 的资产守恒。"""

from __future__ import annotations

import numpy as np
import pytest

from tmo.env.trading_env import TradingEnv


SAMPLE_CONFIG = {
    'exchange': {
        'assets': [{'symbol': 'BTC'}, {'symbol': 'ETH'}, {'symbol': 'USDT'}],
        'pairs': [
            {
                'id': 'BTC/USDT',
                'base': 'BTC',
                'quote': 'USDT',
                'initial_price': 50000.0,
                'tick_size': 1.0,
                'step_size': 0.0001,
                'min_notional': 10.0,
                'n_levels': 5,
                'default_stp_mode': 'expire_maker',
            },
            {
                'id': 'ETH/USDT',
                'base': 'ETH',
                'quote': 'USDT',
                'initial_price': 3000.0,
                'tick_size': 0.1,
                'step_size': 0.001,
                'min_notional': 10.0,
                'n_levels': 5,
                'default_stp_mode': 'expire_maker',
            },
        ],
        'fees': {'maker_fee': 0.001, 'taker_fee': 0.002},
    },
    'agents': {
        'n_agents': 4,
        'initial_holdings': [
            {'BTC': 2.0, 'ETH': 5.0, 'USDT': 80000.0},
            {'BTC': 1.0, 'ETH': 10.0, 'USDT': 100000.0},
            {'BTC': 0.5, 'ETH': 15.0, 'USDT': 120000.0},
            {'BTC': 0.0, 'ETH': 20.0, 'USDT': 150000.0},
        ],
        'max_qty': 100.0,
    },
    'env': {'max_steps': 1000, 'check_negative_equity': False},
}


def _total_assets(env: TradingEnv) -> dict[str, float]:
    """统计所有资产（agent + 交易所）的分项总量。

    Args:
        env: 交易环境实例。

    Returns:
        各资产的总量字典。
    """
    total: dict[str, float] = dict.fromkeys(env._asset_symbols, 0.0)
    for agent in env.possible_agents:
        for sym, qty in env.holdings[agent].items():
            total[sym] += qty
    for sym, qty in env.exchange_holdings.items():
        total[sym] += qty
    return total


def test_asset_conservation_random_episode() -> None:
    """跑完一个随机 episode，断言各资产总量守恒。

    使用随机动作生成交易，验证所有资产（agent 持仓 + 交易所手续费）
    的总量在 episode 前后保持不变。
    """
    from tmo.config.schema import ConfigSchema

    config = ConfigSchema.model_validate(SAMPLE_CONFIG)
    env = TradingEnv(config)
    env.reset(seed=42)

    initial_total = _total_assets(env)

    rng = np.random.default_rng(42)
    n_agents = len(env.possible_agents)
    max_steps = env.config.env.max_steps
    max_iter = max_steps + n_agents

    for _ in range(max_iter):
        agent = env.agent_selection
        if not agent or agent not in env.agents:
            break

        _obs, _reward, termination, truncation, _info = env.last()

        if termination or truncation:
            env.step(None)
        elif rng.random() < 0.1:
            env.step({'asset_id': 0, 'side': 0, 'price': 0.0, 'quantity': 0.0})
        else:
            n_pairs = len(env.config.exchange.pairs)
            asset_id = int(rng.integers(n_pairs))
            side = int(rng.choice([1, 2]))
            pair = env.config.exchange.pairs[asset_id]
            base_price = env.prices.get(pair.base, pair.initial_price)
            price = float(base_price * rng.uniform(0.95, 1.05))
            qty = float(rng.uniform(0.05, 2.0))
            env.step({'asset_id': asset_id, 'side': side, 'price': price, 'quantity': qty})

    final_total = _total_assets(env)

    for sym in env._asset_symbols:
        assert initial_total[sym] == pytest.approx(
            final_total[sym],
            rel=1e-9,
            abs=1e-9,
        ), f'{sym} not conserved: initial={initial_total[sym]}, final={final_total[sym]}'
