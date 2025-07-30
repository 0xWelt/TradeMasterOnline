"""测试价格交叉验证功能."""

import pytest

from tmo.constants import AssetType, OrderStatus, OrderType, TradingPairType
from tmo.trading_pair import TradingPairEngine
from tmo.user import User


class TestPriceCrossingValidation:
    """测试价格交叉验证."""

    def setup_method(self):
        """设置测试环境."""
        self.users = {}
        self.engine = TradingPairEngine(TradingPairType.BTC_USDT, self.users)
        self.user = User(username='test_user', email='test@example.com')
        self.users[self.user.id] = self.user
        # 为用户初始化足够的余额
        self.user.update_total_asset(AssetType.USDT, 100000.0)
        self.user.update_total_asset(AssetType.BTC, 10.0)

    def test_buy_order_below_sell_order_allowed(self):
        """测试买单价格低于卖单价格允许."""
        # 先创建卖单
        sell_order = self.engine.place_order(
            user=self.user,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=51000.0,
        )

        # 创建买单价格低于卖单价格 - 应该成功
        buy_order = self.engine.place_order(
            user=self.user,
            order_type=OrderType.BUY,
            base_amount=1.0,
            price=50000.0,
        )

        assert buy_order.status == OrderStatus.PENDING
        assert sell_order.status == OrderStatus.PENDING
        assert len(self.engine.buy_orders) == 1
        assert len(self.engine.sell_orders) == 1

    def test_sell_order_above_buy_order_allowed(self):
        """测试卖单价格高于买单价格允许."""
        # 先创建买单
        buy_order = self.engine.place_order(
            user=self.user,
            order_type=OrderType.BUY,
            base_amount=1.0,
            price=49000.0,
        )

        # 创建卖单价格高于买单价格 - 应该成功
        sell_order = self.engine.place_order(
            user=self.user,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=50000.0,
        )

        assert buy_order.status == OrderStatus.PENDING
        assert sell_order.status == OrderStatus.PENDING
        assert len(self.engine.buy_orders) == 1
        assert len(self.engine.sell_orders) == 1

    def test_buy_order_above_sell_order_rejected(self):
        """测试买单价格高于卖单价格被拒绝."""
        # 先创建卖单
        self.engine.place_order(
            user=self.user,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=50000.0,
        )

        # 创建买单价格高于卖单价格 - 应该被拒绝
        with pytest.raises(ValueError, match='价格交叉'):
            self.engine.place_order(
                user=self.user,
                order_type=OrderType.BUY,
                base_amount=1.0,
                price=51000.0,
            )

    def test_sell_order_below_buy_order_rejected(self):
        """测试卖单价格低于买单价格被拒绝."""
        # 先创建买单
        self.engine.place_order(
            user=self.user,
            order_type=OrderType.BUY,
            base_amount=1.0,
            price=50000.0,
        )

        # 创建卖单价格低于买单价格 - 应该被拒绝
        with pytest.raises(ValueError, match='价格交叉'):
            self.engine.place_order(
                user=self.user,
                order_type=OrderType.SELL,
                base_amount=1.0,
                price=49000.0,
            )

    def test_equal_prices_allowed(self):
        """测试相等价格允许."""
        # 先创建买单
        buy_order = self.engine.place_order(
            user=self.user,
            order_type=OrderType.BUY,
            base_amount=1.0,
            price=50000.0,
        )

        # 创建相同价格的卖单 - 应该成功并立即成交
        sell_order = self.engine.place_order(
            user=self.user,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=50000.0,
        )

        assert buy_order.status == OrderStatus.FILLED
        assert sell_order.status == OrderStatus.FILLED

    def test_multiple_orders_no_crossing(self):
        """测试多个订单无价格交叉."""
        # 创建多个不同价格的订单
        buy_order1 = self.engine.place_order(
            user=self.user,
            order_type=OrderType.BUY,
            base_amount=1.0,
            price=48000.0,
        )
        buy_order2 = self.engine.place_order(
            user=self.user,
            order_type=OrderType.BUY,
            base_amount=1.0,
            price=49000.0,
        )
        sell_order1 = self.engine.place_order(
            user=self.user,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=51000.0,
        )
        sell_order2 = self.engine.place_order(
            user=self.user,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=52000.0,
        )

        # 所有订单都应该存续
        assert buy_order1.status == OrderStatus.PENDING
        assert buy_order2.status == OrderStatus.PENDING
        assert sell_order1.status == OrderStatus.PENDING
        assert sell_order2.status == OrderStatus.PENDING

    def test_market_orders_no_price_check(self):
        """测试市价订单不检查价格交叉."""
        # 先创建限价卖单
        self.engine.place_order(
            user=self.user,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=50000.0,
        )

        # 创建市价买单 - 应该成功（不检查价格交叉）
        market_buy = self.engine.place_order(
            user=self.user,
            order_type=OrderType.MARKET_BUY,
            quote_amount=1000.0,
        )

        assert market_buy.order_type == OrderType.MARKET_BUY

    def test_different_users_no_interference(self):
        """测试不同用户互不干扰."""
        user2 = User(username='user2', email='user2@example.com')
        user2.update_total_asset(AssetType.USDT, 100000.0)
        user2.update_total_asset(AssetType.BTC, 10.0)

        # 用户1创建买单
        user1_buy = self.engine.place_order(
            user=self.user,
            order_type=OrderType.BUY,
            base_amount=1.0,
            price=48000.0,  # 使用不会匹配的价格
        )

        # 用户2创建卖单价格高于用户1的买单 - 应该成功且不匹配
        user2_sell = self.engine.place_order(
            user=user2,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=52000.0,  # 使用不会匹配的价格
        )

        # 两个订单都应该存续
        assert user1_buy.status == OrderStatus.PENDING
        assert user2_sell.status == OrderStatus.PENDING
