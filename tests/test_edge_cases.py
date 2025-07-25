"""测试边界情况和额外覆盖率"""

import pytest

from tmo.constants import TradingPairType
from tmo.exchange import Exchange
from tmo.typing import AssetType, OrderType


class TestExchangeEdgeCases:
    """测试交易所边界情况"""

    @pytest.fixture
    def exchange(self) -> Exchange:
        """创建交易所实例"""
        return Exchange()

    @pytest.fixture
    def alice(self, exchange: Exchange) -> Exchange:
        """创建Alice用户"""
        return exchange.create_user('alice', 'alice@example.com')

    def test_get_state_snapshot(self, exchange: Exchange, alice: Exchange):
        """测试状态快照功能"""
        snapshot = exchange.get_state_snapshot()
        assert 'assets' in snapshot
        assert 'trading_pairs' in snapshot
        assert 'order_books' in snapshot
        assert 'trades' in snapshot
        assert 'orders' in snapshot
        assert 'users' in snapshot

    def test_get_market_depth(self, exchange: Exchange, alice: Exchange):
        """测试市场深度功能"""
        # 充值并下单
        exchange.deposit(alice, AssetType.USDT, 100000)
        exchange.place_order(
            user=alice,
            order_type=OrderType.BUY,
            asset=AssetType.BTC,
            quantity=1.0,
            price=50000.0,
        )

        depth = exchange.get_market_depth(AssetType.BTC)
        assert 'bids' in depth
        assert 'asks' in depth
        assert len(depth['bids']) == 1
        assert len(depth['asks']) == 0

    def test_get_market_summary(self, exchange: Exchange, alice: Exchange):
        """测试市场摘要功能"""
        # 充值并下单
        exchange.deposit(alice, AssetType.USDT, 100000)
        exchange.place_order(
            user=alice,
            order_type=OrderType.BUY,
            asset=AssetType.BTC,
            quantity=1.0,
            price=50000.0,
        )

        summary = exchange.get_market_summary(AssetType.BTC)
        assert summary['symbol'] == TradingPairType.BTC_USDT.value
        assert summary['current_price'] == 50000.0
        assert summary['total_bids'] == 1
        assert summary['total_asks'] == 0

    def test_get_user_portfolios(self, exchange: Exchange, alice: Exchange):
        """测试获取用户所有持仓"""
        portfolios = exchange.get_user_portfolios(alice)
        assert AssetType.USDT in portfolios
        assert AssetType.BTC in portfolios
        assert portfolios[AssetType.USDT].total_balance == 1000.0

    def test_place_order_with_exact_balance(self, exchange: Exchange, alice: Exchange):
        """测试使用精确余额下单"""
        # Alice初始有1000 USDT
        order = exchange.place_order(
            user=alice,
            order_type=OrderType.BUY,
            asset=AssetType.BTC,
            quantity=0.01,
            price=100000.0,  # 正好使用1000 USDT
        )
        assert order is not None

    def test_withdraw_exact_balance(self, exchange: Exchange, alice: Exchange):
        """测试提现精确余额"""
        # Alice初始有1000 USDT
        exchange.withdraw(alice, AssetType.USDT, 1000.0)
        portfolio = exchange.get_user_portfolio(alice, AssetType.USDT)
        assert portfolio.total_balance == 0.0

    def test_get_market_price(self, exchange: Exchange):
        """测试获取市场价格"""
        price = exchange.get_market_price(AssetType.BTC)
        assert price == 50000.0

    def test_get_trading_pair_info(self, exchange: Exchange):
        """测试获取交易对信息"""
        pair = exchange.get_trading_pair(AssetType.BTC)
        assert pair is not None
        assert pair.symbol == TradingPairType.BTC_USDT.value
        assert pair.base_asset == AssetType.BTC
        assert pair.quote_asset == AssetType.USDT
