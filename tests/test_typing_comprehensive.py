"""综合测试数据模型 - 修复后的版本"""

import pytest

from tmo.typing import (
    AssetType,
    Order,
    OrderType,
    Portfolio,
    TradeSettlement,
    TradingPairType,
    User,
)


class TestOrderComprehensive:
    """测试订单模型 - 修复版本"""

    def test_order_creation_with_user(self):
        """测试订单创建与User对象"""
        user = User(username='testuser', email='test@example.com')
        order = Order(
            user=user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            quantity=1.0,
            price=50000.0,
        )

        assert order.user.id is not None
        assert order.user.username == 'testuser'
        assert order.order_type == OrderType.BUY
        assert order.trading_pair == TradingPairType.BTC_USDT
        assert order.quantity == 1.0
        assert order.price == 50000.0

    def test_order_remaining_quantity(self):
        """测试剩余数量计算"""
        user = User(username='testuser', email='test@example.com')
        order = Order(
            user=user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            quantity=1.0,
            price=50000.0,
            filled_quantity=0.3,
        )

        assert order.remaining_quantity == 0.7

    def test_order_is_filled(self):
        """测试是否完全成交"""
        user = User(username='testuser', email='test@example.com')

        # 未成交
        order1 = Order(
            user=user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            quantity=1.0,
            price=50000.0,
            filled_quantity=0.5,
        )
        assert not order1.is_filled

        # 完全成交
        order2 = Order(
            user=user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            quantity=1.0,
            price=50000.0,
            filled_quantity=1.0,
        )
        assert order2.is_filled

    def test_order_is_partially_filled(self):
        """测试是否部分成交"""
        user = User(username='testuser', email='test@example.com')

        # 未成交
        order1 = Order(
            user=user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            quantity=1.0,
            price=50000.0,
            filled_quantity=0.0,
        )
        assert not order1.is_partially_filled

        # 部分成交
        order2 = Order(
            user=user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            quantity=1.0,
            price=50000.0,
            filled_quantity=0.5,
        )
        assert order2.is_partially_filled

        # 完全成交
        order3 = Order(
            user=user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            quantity=1.0,
            price=50000.0,
            filled_quantity=1.0,
        )
        assert not order3.is_partially_filled


class TestPortfolioComprehensive:
    """测试持仓模型 - 修复版本"""

    def test_portfolio_creation(self):
        """测试持仓创建"""
        portfolio = Portfolio(
            asset=AssetType.BTC,
            available_balance=1.5,
            locked_balance=0.5,
            total_balance=2.0,
        )

        assert portfolio.asset == AssetType.BTC
        assert portfolio.available_balance == 1.5
        assert portfolio.locked_balance == 0.5
        assert portfolio.total_balance == 2.0

    def test_portfolio_negative_validation(self):
        """测试负值验证"""
        with pytest.raises(ValueError):
            Portfolio(asset=AssetType.BTC, available_balance=-1.0)


class TestTradeComprehensive:
    """测试成交记录模型 - 修复版本"""

    def test_trade_creation(self):
        """测试成交记录创建"""
        user1 = User(username='buyer', email='buyer@example.com')
        user2 = User(username='seller', email='seller@example.com')

        buy_order = Order(
            user=user1,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            quantity=1.0,
            price=50000.0,
        )

        sell_order = Order(
            user=user2,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            quantity=1.0,
            price=50000.0,
        )

        trade = TradeSettlement(
            buy_order=buy_order,
            sell_order=sell_order,
            trading_pair=TradingPairType.BTC_USDT,
            quantity=0.5,
            price=50000.0,
        )

        assert trade.trading_pair == TradingPairType.BTC_USDT
        assert trade.quantity == 0.5
        assert trade.price == 50000.0
        assert trade.buy_order.id == buy_order.id
        assert trade.sell_order.id == sell_order.id


class TestUserComprehensive:
    """测试用户模型 - 修复版本"""

    def test_user_creation_with_auto_uuid(self):
        """测试用户创建自动UUID"""
        user = User(username='testuser', email='test@example.com')
        assert user.id is not None
        assert len(user.id) == 36  # UUID 长度
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.created_at is not None
        assert len(user.portfolios) == 0

    def test_update_balance_new_asset(self):
        """测试更新新资产余额"""
        user = User(username='testuser', email='test@example.com')

        # 更新不存在的资产
        user.update_balance(asset=AssetType.USDT, available_change=100.0, locked_change=0.0)

        assert AssetType.USDT in user.portfolios
        portfolio = user.portfolios[AssetType.USDT]
        assert portfolio.available_balance == 100.0
        assert portfolio.total_balance == 100.0

    def test_update_balance_existing_asset(self):
        """测试更新现有资产余额"""
        user = User(username='testuser', email='test@example.com')

        # 先创建资产
        user.portfolios[AssetType.USDT] = Portfolio(
            asset=AssetType.USDT, available_balance=100.0, locked_balance=50.0, total_balance=150.0
        )

        # 更新余额
        user.update_balance(asset=AssetType.USDT, available_change=25.0, locked_change=-25.0)

        portfolio = user.portfolios[AssetType.USDT]
        assert portfolio.available_balance == 125.0
        assert portfolio.locked_balance == 25.0
        assert portfolio.total_balance == 150.0
