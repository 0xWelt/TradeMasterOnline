"""测试 TradingEnv AEC 环境。"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest

from tmo.config.schema import ConfigSchema
from tmo.core.order import Side
from tmo.env.trading_env import TradingEnv


if TYPE_CHECKING:
    from pathlib import Path


SAMPLE_CONFIG = ConfigSchema.model_validate(
    {
        'exchange': {
            'assets': [{'symbol': 'BTC'}, {'symbol': 'USDT'}],
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
                }
            ],
            'fees': {'maker_fee': 0.001, 'taker_fee': 0.002},
        },
        'agents': {
            'n_agents': 2,
            'initial_holdings': {'BTC': 1.0, 'USDT': 100000.0},
            'max_qty': 100.0,
        },
        'env': {'max_steps': 10, 'check_negative_equity': False},
    }
)


class TestTradingEnv:
    def test_reset(self) -> None:
        env = TradingEnv(SAMPLE_CONFIG)
        env.reset(seed=42)
        assert env.agents == ['agent_0', 'agent_1']
        assert env.agent_selection == 'agent_0'
        assert env.prices['BTC'] == 50000.0
        assert env.holdings['agent_0']['BTC'] == 1.0

    def test_observe_shape(self) -> None:
        env = TradingEnv(SAMPLE_CONFIG)
        env.reset()
        obs = env.observe('agent_0')
        assert 'books' in obs
        assert 'holdings' in obs
        assert 'BTC/USDT' in obs['books']
        bids = obs['books']['BTC/USDT']['bids']
        assert isinstance(bids, np.ndarray)
        assert bids.shape == (5, 2)

    def test_hold_action(self) -> None:
        env = TradingEnv(SAMPLE_CONFIG)
        env.reset()
        env.step({'asset_id': 0, 'side': 0, 'price': 0.0, 'quantity': 0.0})
        assert env.agent_selection == 'agent_1'

    def test_place_order_no_match(self) -> None:
        env = TradingEnv(SAMPLE_CONFIG)
        env.reset()
        env.step({'asset_id': 0, 'side': 1, 'price': 40000.0, 'quantity': 0.1})
        assert 'agent_0_1' in env.books['BTC/USDT'].orders
        assert env.agent_selection == 'agent_1'

    def test_place_order_match(self) -> None:
        env = TradingEnv(SAMPLE_CONFIG)
        env.reset()
        # agent_0 sells 0.1 BTC at 50000 (maker)
        env.step({'asset_id': 0, 'side': Side.SELL.value, 'price': 50000.0, 'quantity': 0.1})
        # agent_1 buys 0.1 BTC at 50000 (taker)
        env.step({'asset_id': 0, 'side': Side.BUY.value, 'price': 50000.0, 'quantity': 0.1})
        # Binance-style: fee deducted from received asset
        assert env.holdings['agent_0']['BTC'] == pytest.approx(0.9)
        assert env.holdings['agent_0']['USDT'] == pytest.approx(100000.0 + 5000.0 * 0.999)
        assert env.holdings['agent_1']['BTC'] == pytest.approx(1.0 + 0.1 * 0.998)
        assert env.holdings['agent_1']['USDT'] == pytest.approx(100000.0 - 5000.0)

    def test_insufficient_funds_rejected(self) -> None:
        env = TradingEnv(SAMPLE_CONFIG)
        env.reset()
        env.step({'asset_id': 0, 'side': Side.BUY.value, 'price': 50000.0, 'quantity': 100.0})
        assert 'agent_0_1' not in env.books['BTC/USDT'].orders

    def test_truncation_after_max_steps(self) -> None:
        env = TradingEnv(SAMPLE_CONFIG)
        env.reset()
        for _ in range(20):
            agent = env.agent_selection
            if env.terminations.get(agent) or env.truncations.get(agent):
                env.step(None)
            else:
                env.step({'asset_id': 0, 'side': 0, 'price': 0.0, 'quantity': 0.0})
        assert len(env.agents) == 0

    def test_from_config(self, tmp_path: Path) -> None:
        import yaml

        path = tmp_path / 'cfg.yaml'
        path.write_text(yaml.safe_dump(SAMPLE_CONFIG.model_dump()), encoding='utf-8')
        env = TradingEnv.from_config(str(path))
        env.reset()
        assert env.agents == ['agent_0', 'agent_1']
