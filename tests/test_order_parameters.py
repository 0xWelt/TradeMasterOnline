"""测试订单参数处理逻辑"""

import pytest

from tmo import AssetType, Exchange, OrderType


class TestOrderParameters:
    """测试订单参数处理"""

    def setup_method(self):
        """设置测试环境"""
        self.exchange = Exchange()
        self.user = self.exchange.create_user('test_user', 'test@example.com')
        self.exchange.deposit(self.user, AssetType.USDT, 10000.0)
        self.exchange.deposit(self.user, AssetType.BTC, 1.0)

    def test_limit_order_quantity_only(self):
        """测试限价订单仅指定数量"""
        order = self.exchange.place_order(
            user=self.user,
            order_type=OrderType.BUY,
            asset=AssetType.BTC,
            price=50000.0,
            quantity=0.1,
        )
        assert order.quantity == 0.1
        assert order.amount == 5000.0  # 0.1 * 50000

    def test_limit_order_amount_only(self):
        """测试限价订单仅指定金额"""
        order = self.exchange.place_order(
            user=self.user,
            order_type=OrderType.BUY,
            asset=AssetType.BTC,
            price=50000.0,
            amount=5000.0,
        )
        assert order.quantity == 0.1  # 5000 / 50000
        assert order.amount == 5000.0

    def test_limit_order_both_quantity_and_amount_raises_error(self):
        """测试限价订单同时指定数量和金额应报错"""
        with pytest.raises(ValueError, match='限价订单只能指定数量或金额'):
            self.exchange.place_order(
                user=self.user,
                order_type=OrderType.BUY,
                asset=AssetType.BTC,
                price=50000.0,
                quantity=0.1,
                amount=5000.0,
            )

    def test_limit_order_neither_quantity_nor_amount_raises_error(self):
        """测试限价订单既不指定数量也不指定金额应报错"""
        with pytest.raises(ValueError, match='限价订单必须指定数量或金额'):
            self.exchange.place_order(
                user=self.user,
                order_type=OrderType.BUY,
                asset=AssetType.BTC,
                price=50000.0,
            )

    def test_market_order_amount_only(self):
        """测试市价订单仅指定金额"""
        order = self.exchange.place_order(
            user=self.user,
            order_type=OrderType.MARKET_BUY,
            asset=AssetType.BTC,
            amount=5000.0,
        )
        assert order.amount == 5000.0

    def test_market_order_quantity_raises_error(self):
        """测试市价订单指定数量应报错"""
        with pytest.raises(ValueError, match='市价订单不能指定数量'):
            self.exchange.place_order(
                user=self.user,
                order_type=OrderType.MARKET_BUY,
                asset=AssetType.BTC,
                amount=5000.0,
                quantity=0.1,
            )

    def test_market_order_price_raises_error(self):
        """测试市价订单指定价格应报错"""
        with pytest.raises(ValueError, match='市价订单不能指定价格'):
            self.exchange.place_order(
                user=self.user,
                order_type=OrderType.MARKET_BUY,
                asset=AssetType.BTC,
                amount=5000.0,
                price=50000.0,
            )

    def test_market_order_no_amount_raises_error(self):
        """测试市价订单不指定金额应报错"""
        with pytest.raises(ValueError, match='市价订单必须指定金额'):
            self.exchange.place_order(
                user=self.user,
                order_type=OrderType.MARKET_BUY,
                asset=AssetType.BTC,
            )

    def test_market_sell_order_amount_only(self):
        """测试市价卖单仅指定金额"""
        order = self.exchange.place_order(
            user=self.user,
            order_type=OrderType.MARKET_SELL,
            asset=AssetType.BTC,
            amount=5000.0,
        )
        assert order.amount == 5000.0

    def test_market_sell_order_zero_amount_raises_error(self):
        """测试市价卖单金额为0应报错"""
        with pytest.raises(ValueError, match='市价订单必须指定金额'):
            self.exchange.place_order(
                user=self.user,
                order_type=OrderType.MARKET_SELL,
                asset=AssetType.BTC,
                amount=0.0,
            )

    def test_limit_sell_order_amount_only(self):
        """测试限价卖单仅指定金额"""
        order = self.exchange.place_order(
            user=self.user,
            order_type=OrderType.SELL,
            asset=AssetType.BTC,
            price=50000.0,
            amount=5000.0,
        )
        assert order.quantity == 0.1  # 5000 / 50000
        assert order.amount == 5000.0

    def test_limit_sell_order_quantity_only(self):
        """测试限价卖单仅指定数量"""
        order = self.exchange.place_order(
            user=self.user,
            order_type=OrderType.SELL,
            asset=AssetType.BTC,
            price=50000.0,
            quantity=0.1,
        )
        assert order.quantity == 0.1
        assert order.amount == 5000.0  # 0.1 * 50000
