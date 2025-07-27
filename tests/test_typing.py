"""测试数据模型"""

import pytest

from tmo.constants import TradingPairType
from tmo.typing import (
    Asset,
    AssetType,
    Order,
    OrderType,
    Portfolio,
    TradeSettlement,
    User,
)


class TestAssetType:
    """测试资产类型枚举"""

    def test_asset_types(self):
        """测试资产类型值"""
        assert AssetType.USDT.value == 'USDT'
        assert AssetType.BTC.value == 'BTC'
        assert AssetType.ETH.value == 'ETH'


class TestOrderType:
    """测试订单类型枚举"""

    def test_order_types(self):
        """测试订单类型值"""
        assert OrderType.BUY.value == 'buy'
        assert OrderType.SELL.value == 'sell'


class TestAsset:
    """测试资产模型"""

    def test_asset_creation(self):
        """测试资产创建"""
        asset = Asset(symbol=AssetType.BTC, name='Bitcoin', description='比特币')

        assert asset.symbol == AssetType.BTC
        assert asset.name == 'Bitcoin'
        assert asset.description == '比特币'


class TestOrder:
    """测试订单模型"""

    def test_order_creation(self):
        """测试订单创建"""
        user = User(username='testuser', email='test@example.com')
        order = Order(
            user=user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )

        assert order.id is not None
        assert order.user.id is not None
        assert order.order_type == OrderType.BUY
        assert order.trading_pair == TradingPairType.BTC_USDT
        assert order.base_amount == 1.0
        assert order.price == 50000.0
        assert order.filled_base_amount == 0
        assert order.status == 'pending'

    def test_remaining_base_amount(self):
        """测试剩余数量计算"""
        user = User(username='testuser', email='test@example.com')
        order = Order(
            user=user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
            filled_base_amount=0.3,
        )

        assert order.remaining_base_amount == 0.7

    def test_is_filled(self):
        """测试是否完全成交"""
        user = User(username='testuser', email='test@example.com')
        # 未成交
        order1 = Order(
            user=user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
            filled_base_amount=0.5,
        )
        assert not order1.is_filled

        # 完全成交
        order2 = Order(
            user=user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
            filled_base_amount=1.0,
        )
        assert order2.is_filled

    def test_is_partially_filled(self):
        """测试是否部分成交"""
        user = User(username='testuser', email='test@example.com')
        # 未成交
        order1 = Order(
            user=user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
            filled_base_amount=0.0,
        )
        assert not order1.is_partially_filled

        # 部分成交
        order2 = Order(
            user=user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
            filled_base_amount=0.5,
        )
        assert order2.is_partially_filled

        # 完全成交
        order3 = Order(
            user=user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
            filled_base_amount=1.0,
        )
        assert not order3.is_partially_filled


class TestTradeSettlement:
    """测试成交记录模型"""

    def test_trade_creation(self):
        """测试成交记录创建"""
        user1 = User(username='buyer', email='buyer@example.com')
        user2 = User(username='seller', email='seller@example.com')

        buy_order = Order(
            user=user1,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )

        sell_order = Order(
            user=user2,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )

        settlement = TradeSettlement(
            buy_order=buy_order,
            sell_order=sell_order,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=0.5,
            price=50000.0,
        )

        assert settlement.timestamp is not None
        assert settlement.buy_order.id == buy_order.id
        assert settlement.sell_order.id == sell_order.id
        assert settlement.trading_pair == TradingPairType.BTC_USDT
        assert settlement.base_amount == 0.5
        assert settlement.price == 50000.0


class TestUser:
    """测试用户模型"""

    def test_user_creation(self):
        """测试用户创建"""
        user = User(username='testuser', email='test@example.com')
        assert user.id is not None
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


class TestPortfolio:
    """测试持仓模型"""

    def test_portfolio_creation(self):
        """测试持仓创建"""
        portfolio = Portfolio(
            asset=AssetType.BTC, available_balance=1.5, locked_balance=0.5, total_balance=2.0
        )
        assert portfolio.asset == AssetType.BTC
        assert portfolio.available_balance == 1.5
        assert portfolio.locked_balance == 0.5
        assert portfolio.total_balance == 2.0

    def test_portfolio_negative_validation(self):
        """测试负值验证"""
        with pytest.raises(ValueError):
            Portfolio(asset=AssetType.BTC, available_balance=-1.0)


class TestOrderCallbacks:
    """测试订单回调"""

    def test_on_filled_buy_order(self):
        """测试买单成交回调"""
        user = User(username='testuser', email='test@example.com')
        user.portfolios[AssetType.USDT] = Portfolio(
            asset=AssetType.USDT, available_balance=1000, locked_balance=500
        )
        # 确保BTC持仓存在
        user.portfolios[AssetType.BTC] = Portfolio(
            asset=AssetType.BTC, available_balance=0, locked_balance=0
        )

        order = Order(
            user=user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=500.0,
        )

        # 创建对应的卖单
        seller = User(username='seller', email='seller@example.com')
        sell_order = Order(
            user=seller,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=500.0,
        )

        trade = TradeSettlement(
            buy_order=order,
            sell_order=sell_order,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=500.0,
        )

        # on_filled已废弃，直接测试余额更新逻辑
        # 模拟TradeSettlement层面的余额更新
        buyer = order.user

        # 买家操作：获得基础资产，减少计价资产
        buyer.update_balance(
            asset=trade.trading_pair.base_asset,
            available_change=trade.base_amount,
            locked_change=-trade.base_amount,
        )
        buyer.update_balance(
            asset=trade.trading_pair.quote_asset,
            available_change=-trade.base_amount * trade.price,
            locked_change=0,
        )

        # 验证BTC余额：获得1.0 BTC
        btc_portfolio = user.portfolios[AssetType.BTC]
        usdt_portfolio = user.portfolios[AssetType.USDT]
        assert btc_portfolio.available_balance == 1.0
        assert usdt_portfolio.available_balance == 500.0  # 1000 - 500

    def test_on_filled_sell_order(self):
        """测试卖单成交回调"""
        user = User(username='testuser', email='test@example.com')
        user.portfolios[AssetType.BTC] = Portfolio(
            asset=AssetType.BTC, available_balance=2.0, locked_balance=1.0
        )
        # 确保USDT持仓存在
        user.portfolios[AssetType.USDT] = Portfolio(
            asset=AssetType.USDT, available_balance=0, locked_balance=0
        )

        order = Order(
            user=user,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=500.0,
        )

        # 创建对应的买单
        buyer = User(username='buyer', email='buyer@example.com')
        buy_order = Order(
            user=buyer,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=500.0,
        )

        trade = TradeSettlement(
            buy_order=buy_order,
            sell_order=order,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=500.0,
        )

        # on_filled已废弃，直接测试余额更新逻辑
        # 模拟TradeSettlement层面的余额更新
        seller = order.user

        # 卖家操作：获得计价资产，减少基础资产
        seller.update_balance(
            asset=trade.trading_pair.quote_asset,
            available_change=trade.base_amount * trade.price,
            locked_change=0,
        )
        seller.update_balance(
            asset=trade.trading_pair.base_asset,
            available_change=0,
            locked_change=-trade.base_amount,
        )

        # 验证余额更新
        btc_portfolio = user.portfolios[AssetType.BTC]
        usdt_portfolio = user.portfolios[AssetType.USDT]
        assert btc_portfolio.available_balance == 2.0  # 剩余可用
        assert btc_portfolio.locked_balance == 0.0  # 释放锁定
        assert btc_portfolio.total_balance == 2.0
        assert usdt_portfolio.available_balance == 500.0  # 获得USDT
        assert usdt_portfolio.locked_balance == 0.0

    def test_on_cancelled_buy_order(self):
        """测试买单取消回调"""
        user = User(username='testuser', email='test@example.com')
        user.portfolios[AssetType.USDT] = Portfolio(
            asset=AssetType.USDT, available_balance=500, locked_balance=500
        )

        order = Order(
            user=user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=500.0,
        )

        order.on_cancelled()

        # 验证USDT释放
        usdt_portfolio = user.portfolios[AssetType.USDT]
        assert usdt_portfolio.available_balance == 1000.0
        assert usdt_portfolio.locked_balance == 0.0

    def test_on_cancelled_sell_order(self):
        """测试卖单取消回调"""
        user = User(username='testuser', email='test@example.com')
        user.portfolios[AssetType.BTC] = Portfolio(
            asset=AssetType.BTC, available_balance=1.0, locked_balance=1.0
        )

        order = Order(
            user=user,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=500.0,
        )

        order.on_cancelled()

        # 验证BTC释放
        btc_portfolio = user.portfolios[AssetType.BTC]
        assert btc_portfolio.available_balance == 2.0
        assert btc_portfolio.locked_balance == 0.0

    def test_callbacks_with_none_user(self):
        """测试用户为None时的回调 - 跳过测试，因为User字段现在是必需的"""
        # 由于User字段现在是必需的，这个测试用例不再适用
        # 实际的回调处理逻辑中仍然处理了user为None的情况

    def test_user_consistency_validation(self):
        """测试用户一致性验证"""
        user1 = User(username='testuser', email='test@example.com')

        # 应该通过验证
        order = Order(
            user=user1,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=500.0,
        )
        assert order.user_id == user1.id
