"""测试数据模型"""

from tmo.typing import Asset, AssetType, Order, OrderType, Trade, TradingPair


class TestAssetType:
    """测试资产类型枚举"""

    def test_asset_types(self):
        """测试资产类型值"""
        assert AssetType.USDT.value == 'USDT'
        assert AssetType.BTC.value == 'BTC'


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
        order = Order(
            id='test-order-1',
            user_id='user1',
            order_type=OrderType.BUY,
            asset=AssetType.BTC,
            quantity=1.0,
            price=50000.0,
        )

        assert order.id == 'test-order-1'
        assert order.user_id == 'user1'
        assert order.order_type == OrderType.BUY
        assert order.asset == AssetType.BTC
        assert order.quantity == 1.0
        assert order.price == 50000.0
        assert order.filled_quantity == 0
        assert order.status == 'pending'

    def test_remaining_quantity(self):
        """测试剩余数量计算"""
        order = Order(
            id='test-order-1',
            user_id='user1',
            order_type=OrderType.BUY,
            asset=AssetType.BTC,
            quantity=1.0,
            price=50000.0,
            filled_quantity=0.3,
        )

        assert order.remaining_quantity == 0.7

    def test_is_filled(self):
        """测试是否完全成交"""
        # 未成交
        order1 = Order(
            id='test-order-1',
            user_id='user1',
            order_type=OrderType.BUY,
            asset=AssetType.BTC,
            quantity=1.0,
            price=50000.0,
            filled_quantity=0.5,
        )
        assert not order1.is_filled

        # 完全成交
        order2 = Order(
            id='test-order-2',
            user_id='user1',
            order_type=OrderType.BUY,
            asset=AssetType.BTC,
            quantity=1.0,
            price=50000.0,
            filled_quantity=1.0,
        )
        assert order2.is_filled

    def test_is_partially_filled(self):
        """测试是否部分成交"""
        # 未成交
        order1 = Order(
            id='test-order-1',
            user_id='user1',
            order_type=OrderType.BUY,
            asset=AssetType.BTC,
            quantity=1.0,
            price=50000.0,
            filled_quantity=0.0,
        )
        assert not order1.is_partially_filled

        # 部分成交
        order2 = Order(
            id='test-order-2',
            user_id='user1',
            order_type=OrderType.BUY,
            asset=AssetType.BTC,
            quantity=1.0,
            price=50000.0,
            filled_quantity=0.5,
        )
        assert order2.is_partially_filled

        # 完全成交
        order3 = Order(
            id='test-order-3',
            user_id='user1',
            order_type=OrderType.BUY,
            asset=AssetType.BTC,
            quantity=1.0,
            price=50000.0,
            filled_quantity=1.0,
        )
        assert not order3.is_partially_filled


class TestTrade:
    """测试成交记录模型"""

    def test_trade_creation(self):
        """测试成交记录创建"""
        trade = Trade(
            id='test-trade-1',
            buy_order_id='buy-order-1',
            sell_order_id='sell-order-1',
            asset=AssetType.BTC,
            quantity=0.5,
            price=50000.0,
        )

        assert trade.id == 'test-trade-1'
        assert trade.buy_order_id == 'buy-order-1'
        assert trade.sell_order_id == 'sell-order-1'
        assert trade.asset == AssetType.BTC
        assert trade.quantity == 0.5
        assert trade.price == 50000.0


class TestTradingPair:
    """测试交易对模型"""

    def test_trading_pair_creation(self):
        """测试交易对创建"""
        pair = TradingPair(
            base_asset=AssetType.BTC, quote_asset=AssetType.USDT, current_price=50000.0
        )

        assert pair.base_asset == AssetType.BTC
        assert pair.quote_asset == AssetType.USDT
        assert pair.current_price == 50000.0
        assert pair.symbol == 'BTC/USDT'

    def test_symbol_property(self):
        """测试交易对符号属性"""
        pair = TradingPair(
            base_asset=AssetType.BTC, quote_asset=AssetType.USDT, current_price=50000.0
        )

        assert pair.symbol == 'BTC/USDT'
