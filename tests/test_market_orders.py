"""测试市价订单功能"""

import pytest

from tmo import AssetType, Exchange, OrderType
from tmo.constants import TradingPairType


class TestMarketOrders:
    """测试市价订单"""

    def setup_method(self):
        """设置测试环境"""
        self.exchange = Exchange()
        self.user1 = self.exchange.create_user('user1', 'user1@example.com')
        self.user2 = self.exchange.create_user('user2', 'user2@example.com')

        # 设置初始余额
        self.exchange.deposit(self.user1, AssetType.USDT, 50000.0)
        self.exchange.deposit(self.user1, AssetType.BTC, 1.0)
        self.exchange.deposit(self.user2, AssetType.USDT, 50000.0)
        self.exchange.deposit(self.user2, AssetType.BTC, 1.0)

    def test_market_buy_with_existing_orders(self):
        """测试存在限价卖单时的市价买入"""
        # 先下限价卖单
        self.exchange.place_order(
            user=self.user2,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            price=50000.0,
            base_amount=0.5,
        )

        # 下市价买单
        order = self.exchange.place_order(
            user=self.user1,
            order_type=OrderType.MARKET_BUY,
            trading_pair=TradingPairType.BTC_USDT,
            quote_amount=25000.0,
        )

        assert order.status in ['filled', 'partially_filled']
        assert order.filled_base_amount > 0

    def test_market_sell_with_existing_orders(self):
        """测试存在限价买单时的市价卖出"""
        # 先下限价买单
        self.exchange.place_order(
            user=self.user2,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            price=50000.0,
            base_amount=0.5,
        )

        # 下市价卖单
        order = self.exchange.place_order(
            user=self.user1,
            order_type=OrderType.MARKET_SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=0.5,  # 卖出0.5 BTC
        )

        assert order.status in ['filled', 'partially_filled']
        assert order.filled_base_amount > 0

    def test_market_buy_insufficient_balance(self):
        """测试市价买入余额不足"""
        # 创建一个余额不足的用户
        poor_user = self.exchange.create_user('poor', 'poor@example.com')
        with pytest.raises(ValueError, match='USDT余额不足'):
            self.exchange.place_order(
                user=poor_user,
                order_type=OrderType.MARKET_BUY,
                trading_pair=TradingPairType.BTC_USDT,
                quote_amount=20000.0,  # 超过1000 USDT初始余额
            )

    def test_market_sell_insufficient_balance(self):
        """测试市价卖出余额不足"""
        with pytest.raises(ValueError, match='BTC余额不足'):
            self.exchange.place_order(
                user=self.user1,
                order_type=OrderType.MARKET_SELL,
                trading_pair=TradingPairType.BTC_USDT,
                base_amount=100000.0,  # 需要卖出100000 BTC，但只有1 BTC
            )

    def test_market_order_with_no_matching_orders(self):
        """测试无匹配订单的市价订单"""
        # 清空订单簿
        engine = self.exchange.trading_pair_engines[TradingPairType.BTC_USDT.value]
        engine.buy_orders.clear()
        engine.sell_orders.clear()

        # 下市价买单，应该部分成交或保持未成交状态
        order = self.exchange.place_order(
            user=self.user1,
            order_type=OrderType.MARKET_BUY,
            trading_pair=TradingPairType.BTC_USDT,
            quote_amount=1000.0,
        )

        # 没有限价订单，市价订单无法成交
        assert order.status == 'pending' or order.filled_base_amount == 0

    def test_market_order_partial_fill(self):
        """测试市价订单部分成交"""
        # 下限价卖单
        self.exchange.place_order(
            user=self.user2,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            price=50000.0,
            base_amount=0.1,  # 少量卖单
        )

        # 下大额市价买单，应该部分成交
        order = self.exchange.place_order(
            user=self.user1,
            order_type=OrderType.MARKET_BUY,
            trading_pair=TradingPairType.BTC_USDT,
            quote_amount=10000.0,  # 需要0.2 BTC，但只有0.1 BTC卖单
        )

        assert order.filled_base_amount == 0.1
        assert order.status == 'partially_filled'
