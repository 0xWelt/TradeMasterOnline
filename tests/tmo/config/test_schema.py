"""测试配置模型。"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from tmo.config.schema import ConfigSchema


if TYPE_CHECKING:
    from pathlib import Path


SAMPLE_CONFIG = {
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
    'env': {'max_steps': 100, 'check_negative_equity': False},
}


class TestConfigSchema:
    def test_from_dict(self) -> None:
        cfg = ConfigSchema.model_validate(SAMPLE_CONFIG)
        assert cfg.exchange.pairs[0].id == 'BTC/USDT'
        assert cfg.agents.n_agents == 2
        assert cfg.env.max_steps == 100

    def test_from_yaml_file(self, tmp_path: Path) -> None:
        path = tmp_path / 'config.yaml'
        path.write_text(yaml.safe_dump(SAMPLE_CONFIG), encoding='utf-8')
        cfg = ConfigSchema.from_yaml(str(path))
        assert cfg.exchange.assets[0].symbol == 'BTC'

    def test_invalid_pair_asset(self) -> None:
        bad = {
            'exchange': {
                'assets': [{'symbol': 'BTC'}],
                'pairs': [
                    {
                        'id': 'BTC/USDT',
                        'base': 'BTC',
                        'quote': 'USDT',
                        'initial_price': 1.0,
                        'tick_size': 1.0,
                        'step_size': 0.0001,
                        'min_notional': 10.0,
                        'default_stp_mode': 'expire_maker',
                        'n_levels': 1,
                    }
                ],
                'fees': {'maker_fee': 0.0, 'taker_fee': 0.0},
            },
            'agents': {
                'n_agents': 1,
                'initial_holdings': {},
                'max_qty': 1.0,
            },
            'env': {'max_steps': 1},
        }
        with pytest.raises(ValueError, match='not in assets'):
            ConfigSchema.model_validate(bad)

    def test_negative_fee_rejected(self) -> None:
        bad = {
            'exchange': {
                'assets': [{'symbol': 'BTC'}, {'symbol': 'USDT'}],
                'pairs': [
                    {
                        'id': 'BTC/USDT',
                        'base': 'BTC',
                        'quote': 'USDT',
                        'initial_price': 1.0,
                        'tick_size': 1.0,
                        'step_size': 0.0001,
                        'min_notional': 10.0,
                        'default_stp_mode': 'expire_maker',
                        'n_levels': 1,
                    }
                ],
                'fees': {'maker_fee': -0.001, 'taker_fee': 0.0},
            },
            'agents': {
                'n_agents': 1,
                'initial_holdings': {},
                'max_qty': 1.0,
            },
            'env': {'max_steps': 1},
        }
        with pytest.raises(ValueError, match='greater than or equal to 0'):
            ConfigSchema.model_validate(bad)

    def test_differentiated_holdings(self) -> None:
        cfg = ConfigSchema.model_validate(
            {
                'exchange': {
                    'assets': [{'symbol': 'BTC'}, {'symbol': 'USDT'}],
                    'pairs': [
                        {
                            'id': 'BTC/USDT',
                            'base': 'BTC',
                            'quote': 'USDT',
                            'initial_price': 1.0,
                            'tick_size': 1.0,
                            'step_size': 0.0001,
                            'min_notional': 10.0,
                            'n_levels': 1,
                            'default_stp_mode': 'expire_maker',
                        }
                    ],
                    'fees': {'maker_fee': 0.0, 'taker_fee': 0.0},
                },
                'agents': {
                    'n_agents': 2,
                    'initial_holdings': [
                        {'BTC': 2.0, 'USDT': 100.0},
                        {'BTC': 0.5, 'USDT': 200.0},
                    ],
                    'max_qty': 1.0,
                },
                'env': {'max_steps': 1},
            }
        )
        holdings = cfg.agents.initial_holdings
        assert isinstance(holdings, list)
        assert holdings[0]['BTC'] == 2.0
        assert holdings[1]['BTC'] == 0.5

    def test_differentiated_holdings_length_mismatch(self) -> None:
        bad = {
            'exchange': {
                'assets': [{'symbol': 'BTC'}, {'symbol': 'USDT'}],
                'pairs': [
                    {
                        'id': 'BTC/USDT',
                        'base': 'BTC',
                        'quote': 'USDT',
                        'initial_price': 1.0,
                        'tick_size': 1.0,
                        'step_size': 0.0001,
                        'min_notional': 10.0,
                        'n_levels': 1,
                        'default_stp_mode': 'expire_maker',
                    }
                ],
                'fees': {'maker_fee': 0.0, 'taker_fee': 0.0},
            },
            'agents': {
                'n_agents': 2,
                'initial_holdings': [
                    {'BTC': 1.0, 'USDT': 100.0},
                ],
                'max_qty': 1.0,
            },
            'env': {'max_steps': 1},
        }
        with pytest.raises(ValueError, match='must equal n_agents'):
            ConfigSchema.model_validate(bad)
