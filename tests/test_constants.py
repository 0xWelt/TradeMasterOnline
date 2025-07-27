"""测试 tmo/constants.py 的枚举定义."""

from tmo.constants import AssetType, OrderStatus, OrderType, TradingPairType


class TestAssetType:
    """测试资产类型枚举."""

    def test_asset_type_values(self):
        """测试资产类型的枚举值."""
        assert AssetType.USDT == 'USDT'
        assert AssetType.BTC == 'BTC'
        assert AssetType.ETH == 'ETH'

    def test_asset_type_members(self):
        """测试资产类型的成员."""
        assert len(AssetType) == 3
        assert 'USDT' in [member.value for member in AssetType]
        assert 'BTC' in [member.value for member in AssetType]
        assert 'ETH' in [member.value for member in AssetType]

    def test_initial_value_property(self):
        """测试资产的初始价值属性."""
        assert AssetType.USDT.initial_value == 1.0
        assert AssetType.BTC.initial_value == 50000.0
        assert AssetType.ETH.initial_value == 3000.0

    def test_initial_value_type(self):
        """测试初始价值的数据类型."""
        assert isinstance(AssetType.USDT.initial_value, float)
        assert isinstance(AssetType.BTC.initial_value, float)
        assert isinstance(AssetType.ETH.initial_value, float)

    def test_initial_value_consistency(self):
        """测试初始价值的一致性."""
        # 确保所有资产都有初始价值
        for asset in AssetType:
            assert isinstance(asset.initial_value, float)
            assert asset.initial_value > 0


class TestOrderType:
    """测试订单类型枚举."""

    def test_order_type_values(self):
        """测试订单类型的枚举值."""
        assert OrderType.BUY == 'buy'
        assert OrderType.SELL == 'sell'
        assert OrderType.MARKET_BUY == 'market_buy'
        assert OrderType.MARKET_SELL == 'market_sell'

    def test_order_type_members(self):
        """测试订单类型的成员."""
        assert len(OrderType) == 4
        expected_values = {'buy', 'sell', 'market_buy', 'market_sell'}
        actual_values = {member.value for member in OrderType}
        assert actual_values == expected_values

    def test_order_type_string_enum(self):
        """测试订单类型是字符串枚举."""
        for order_type in OrderType:
            assert isinstance(order_type.value, str)


class TestOrderStatus:
    """测试订单状态枚举."""

    def test_order_status_values(self):
        """测试订单状态的枚举值."""
        assert OrderStatus.PENDING == 'pending'
        assert OrderStatus.PARTIALLY_FILLED == 'partially_filled'
        assert OrderStatus.FILLED == 'filled'
        assert OrderStatus.CANCELLED == 'cancelled'

    def test_order_status_members(self):
        """测试订单状态的成员."""
        assert len(OrderStatus) == 4
        expected_values = {'pending', 'partially_filled', 'filled', 'cancelled'}
        actual_values = {member.value for member in OrderStatus}
        assert actual_values == expected_values

    def test_order_status_string_enum(self):
        """测试订单状态是字符串枚举."""
        for status in OrderStatus:
            assert isinstance(status.value, str)


class TestTradingPairType:
    """测试交易对类型枚举."""

    def test_trading_pair_values(self):
        """测试交易对的枚举值."""
        assert TradingPairType.BTC_USDT == 'BTC/USDT'
        assert TradingPairType.ETH_USDT == 'ETH/USDT'
        assert TradingPairType.ETH_BTC == 'ETH/BTC'

    def test_trading_pair_members(self):
        """测试交易对的成员."""
        assert len(TradingPairType) == 3
        expected_values = {'BTC/USDT', 'ETH/USDT', 'ETH/BTC'}
        actual_values = {member.value for member in TradingPairType}
        assert actual_values == expected_values

    def test_base_asset_property(self):
        """测试基础资产属性."""
        assert TradingPairType.BTC_USDT.base_asset == AssetType.BTC
        assert TradingPairType.ETH_USDT.base_asset == AssetType.ETH
        assert TradingPairType.ETH_BTC.base_asset == AssetType.ETH

    def test_quote_asset_property(self):
        """测试计价资产属性."""
        assert TradingPairType.BTC_USDT.quote_asset == AssetType.USDT
        assert TradingPairType.ETH_USDT.quote_asset == AssetType.USDT
        assert TradingPairType.ETH_BTC.quote_asset == AssetType.BTC

    def test_base_quote_asset_types(self):
        """测试基础资产和计价资产的类型."""
        for pair in TradingPairType:
            assert isinstance(pair.base_asset, AssetType)
            assert isinstance(pair.quote_asset, AssetType)

    def test_initial_price_property(self):
        """测试初始价格属性."""
        assert TradingPairType.BTC_USDT.initial_price == 50000.0
        assert TradingPairType.ETH_USDT.initial_price == 3000.0
        assert TradingPairType.ETH_BTC.initial_price == 0.06

    def test_initial_price_type(self):
        """测试初始价格的数据类型."""
        for pair in TradingPairType:
            assert isinstance(pair.initial_price, float)
            assert pair.initial_price > 0

    def test_base_quote_consistency(self):
        """测试基础资产和计价资产的一致性."""
        for pair in TradingPairType:
            base, quote = pair.value.split('/')
            assert pair.base_asset == AssetType(base)
            assert pair.quote_asset == AssetType(quote)

    def test_trading_pair_string_representation(self):
        """测试交易对的字符串表示."""
        assert str(TradingPairType.BTC_USDT) == 'BTC/USDT'
        assert str(TradingPairType.ETH_USDT) == 'ETH/USDT'
        assert str(TradingPairType.ETH_BTC) == 'ETH/BTC'
