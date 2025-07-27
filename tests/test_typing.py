"""测试 tmo/typing.py 的数据模型."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from tmo.constants import AssetType, OrderStatus, OrderType, TradingPairType
from tmo.typing import Asset, Order, Portfolio, TradeSettlement, User


class TestAsset:
    """测试资产模型."""

    def test_asset_creation(self):
        """测试资产创建."""
        asset = Asset(symbol=AssetType.BTC, name='Bitcoin')
        assert asset.symbol == AssetType.BTC
        assert asset.name == 'Bitcoin'
        assert asset.description == ''

    def test_asset_with_description(self):
        """测试带描述的资产创建."""
        asset = Asset(
            symbol=AssetType.USDT,
            name='Tether USD',
            description='A stablecoin pegged to the US dollar',
        )
        assert asset.symbol == AssetType.USDT
        assert asset.name == 'Tether USD'
        assert asset.description == 'A stablecoin pegged to the US dollar'

    def test_asset_immutable_fields(self):
        """测试资产字段不可变性."""
        asset = Asset(symbol=AssetType.ETH, name='Ethereum')
        with pytest.raises(ValidationError):
            asset.symbol = AssetType.BTC

    def test_asset_validation(self):
        """测试资产验证."""
        # 测试无效的资产类型
        with pytest.raises(ValidationError):
            Asset(symbol='INVALID', name='Invalid')


class TestPortfolio:
    """测试持仓模型."""

    def test_portfolio_creation(self):
        """测试持仓创建."""
        portfolio = Portfolio(asset=AssetType.BTC)
        assert portfolio.asset == AssetType.BTC
        assert portfolio.available_balance == 0
        assert portfolio.locked_balance == 0
        assert portfolio.total_balance == 0

    def test_portfolio_with_balances(self):
        """测试带余额的持仓创建."""
        portfolio = Portfolio(
            asset=AssetType.USDT,
            available_balance=1000.0,
            locked_balance=500.0,
        )
        assert portfolio.available_balance == 1000.0
        assert portfolio.locked_balance == 500.0
        assert portfolio.total_balance == 1500.0

    def test_total_balance_calculation(self):
        """测试总余额计算."""
        portfolio = Portfolio(asset=AssetType.ETH)
        portfolio.available_balance = 10.0
        portfolio.locked_balance = 5.0
        assert portfolio.total_balance == 15.0

    def test_negative_balance_validation(self):
        """测试负余额验证."""
        with pytest.raises(ValidationError):
            Portfolio(asset=AssetType.BTC, available_balance=-1.0)
        with pytest.raises(ValidationError):
            Portfolio(asset=AssetType.BTC, locked_balance=-1.0)

    def test_portfolio_immutable_asset(self):
        """测试资产类型不可变."""
        portfolio = Portfolio(asset=AssetType.USDT)
        with pytest.raises(ValidationError):
            portfolio.asset = AssetType.BTC


class TestUser:
    """测试用户模型."""

    def test_user_creation(self):
        """测试用户创建."""
        user = User(username='test_user', email='test@example.com')
        assert user.username == 'test_user'
        assert user.email == 'test@example.com'
        assert isinstance(user.id, str)
        assert isinstance(user.created_at, datetime)
        assert user.portfolios == {}

    def test_user_portfolios(self):
        """测试用户持仓."""
        portfolio = Portfolio(asset=AssetType.BTC)
        user = User(
            username='test_user',
            email='test@example.com',
            portfolios={AssetType.BTC: portfolio},
        )
        assert AssetType.BTC in user.portfolios
        assert user.portfolios[AssetType.BTC] == portfolio

    def test_user_update_balance_new_asset(self):
        """测试为新资产更新余额."""
        user = User(username='test_user', email='test@example.com')
        user.update_balance(AssetType.BTC, 1.5, 0.5)
        assert AssetType.BTC in user.portfolios
        assert user.portfolios[AssetType.BTC].available_balance == 1.5
        assert user.portfolios[AssetType.BTC].locked_balance == 0.5

    def test_user_update_balance_existing_asset(self):
        """测试为已有资产更新余额."""
        user = User(username='test_user', email='test@example.com')
        user.update_balance(AssetType.USDT, 1000.0, 0.0)
        user.update_balance(AssetType.USDT, 500.0, 200.0)
        assert user.portfolios[AssetType.USDT].available_balance == 1500.0
        assert user.portfolios[AssetType.USDT].locked_balance == 200.0

    def test_user_immutable_fields(self):
        """测试用户字段不可变性."""
        user = User(username='test_user', email='test@example.com')
        with pytest.raises(ValidationError):
            user.username = 'new_username'
        with pytest.raises(ValidationError):
            user.email = 'new@example.com'

    def test_auto_generated_fields(self):
        """测试自动生成字段."""
        user1 = User(username='test_user', email='test@example.com')
        user2 = User(username='test_user', email='test@example.com')
        assert user1.id != user2.id
        assert user1.created_at != user2.created_at


class TestOrder:
    """测试订单模型."""

    def setup_method(self):
        """设置测试用户."""
        self.user = User(username='test_user', email='test@example.com')

    def test_limit_buy_order(self):
        """测试限价买单创建."""
        order = Order(
            user=self.user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        assert order.order_type == OrderType.BUY
        assert order.trading_pair == TradingPairType.BTC_USDT
        assert order.base_amount == 1.0
        assert order.price == 50000.0
        assert order.quote_amount is None
        assert order.status == OrderStatus.PENDING

    def test_limit_sell_order(self):
        """测试限价卖单创建."""
        order = Order(
            user=self.user,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=0.5,
            price=51000.0,
        )
        assert order.order_type == OrderType.SELL
        assert order.base_amount == 0.5
        assert order.price == 51000.0

    def test_market_buy_order(self):
        """测试市价买单创建."""
        order = Order(
            user=self.user,
            order_type=OrderType.MARKET_BUY,
            trading_pair=TradingPairType.BTC_USDT,
            quote_amount=1000.0,
        )
        assert order.order_type == OrderType.MARKET_BUY
        assert order.quote_amount == 1000.0
        assert order.price is None
        assert order.base_amount is None

    def test_market_sell_order(self):
        """测试市价卖单创建."""
        order = Order(
            user=self.user,
            order_type=OrderType.MARKET_SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=0.1,
        )
        assert order.order_type == OrderType.MARKET_SELL
        assert order.base_amount == 0.1
        assert order.price is None

    def test_order_validation_invalid_price_for_market(self):
        """测试市价订单不能指定价格."""
        with pytest.raises(ValidationError, match='市价订单不能指定价格'):
            Order(
                user=self.user,
                order_type=OrderType.MARKET_BUY,
                trading_pair=TradingPairType.BTC_USDT,
                base_amount=1.0,
                price=50000.0,
            )

    def test_order_validation_missing_price_for_limit(self):
        """测试限价订单必须指定价格 - 通过测试零价格触发验证."""
        with pytest.raises(ValidationError, match='限价订单价格必须大于0'):
            Order(
                user=self.user,
                order_type=OrderType.BUY,
                trading_pair=TradingPairType.BTC_USDT,
                base_amount=1.0,
                price=0,
            )

    def test_order_validation_zero_price(self):
        """测试价格必须大于0."""
        with pytest.raises(ValidationError, match='限价订单价格必须大于0'):
            Order(
                user=self.user,
                order_type=OrderType.BUY,
                trading_pair=TradingPairType.BTC_USDT,
                base_amount=1.0,
                price=0,
            )

    def test_order_validation_zero_amount(self):
        """测试数量必须大于0."""
        with pytest.raises(ValidationError, match='基础资产数量必须大于0'):
            Order(
                user=self.user,
                order_type=OrderType.BUY,
                trading_pair=TradingPairType.BTC_USDT,
                base_amount=0,
                price=50000.0,
            )

    def test_order_validation_mutual_exclusion(self):
        """测试基础资产数量和计价资产金额的互斥性."""
        with pytest.raises(ValidationError, match='基础资产数量和计价资产金额只能设置一个'):
            Order(
                user=self.user,
                order_type=OrderType.BUY,
                trading_pair=TradingPairType.BTC_USDT,
                base_amount=1.0,
                quote_amount=50000.0,
                price=50000.0,
            )

    def test_order_validation_missing_amount(self):
        """测试必须设置数量."""
        with pytest.raises(ValidationError, match='必须设置基础资产数量或计价资产金额'):
            Order(
                user=self.user,
                order_type=OrderType.BUY,
                trading_pair=TradingPairType.BTC_USDT,
                price=50000.0,
            )

    def test_order_properties(self):
        """测试订单属性."""
        order = Order(
            user=self.user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        assert order.user_id == self.user.id
        assert order.remaining_base_amount == 1.0
        assert not order.is_filled
        assert not order.is_partially_filled

    def test_order_filled_status(self):
        """测试订单成交状态."""
        order = Order(
            user=self.user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        order.filled_base_amount = 1.0
        assert order.is_filled
        assert not order.is_partially_filled

    def test_order_partially_filled_status(self):
        """测试订单部分成交状态."""
        order = Order(
            user=self.user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        order.filled_base_amount = 0.5
        assert order.is_partially_filled
        assert not order.is_filled

    def test_order_cancelled_callback(self):
        """测试订单取消回调."""
        # 为用户设置初始余额
        self.user.update_balance(AssetType.USDT, 100000.0, 0.0)

        order = Order(
            user=self.user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )

        # 模拟锁定余额
        self.user.update_balance(AssetType.USDT, -50000.0, 50000.0)

        # 取消订单
        order.on_cancelled()
        assert self.user.portfolios[AssetType.USDT].available_balance == 100000.0
        assert self.user.portfolios[AssetType.USDT].locked_balance == 0.0

    def test_auto_generated_fields(self):
        """测试自动生成字段."""
        order1 = Order(
            user=self.user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        order2 = Order(
            user=self.user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        assert order1.id != order2.id


class TestTradeSettlement:
    """测试交易结算模型."""

    def setup_method(self):
        """设置测试用户和订单."""
        self.buy_user = User(username='buyer', email='buyer@example.com')
        self.sell_user = User(username='seller', email='seller@example.com')

        self.buy_order = Order(
            user=self.buy_user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )

        self.sell_order = Order(
            user=self.sell_user,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )

    def test_trade_settlement_creation(self):
        """测试交易结算创建."""
        trade = TradeSettlement(
            buy_order=self.buy_order,
            sell_order=self.sell_order,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        assert trade.buy_order == self.buy_order
        assert trade.sell_order == self.sell_order
        assert trade.trading_pair == TradingPairType.BTC_USDT
        assert trade.base_amount == 1.0
        assert trade.price == 50000.0
        assert isinstance(trade.timestamp, datetime)

    def test_trade_settlement_properties(self):
        """测试交易结算属性."""
        trade = TradeSettlement(
            buy_order=self.buy_order,
            sell_order=self.sell_order,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        assert trade.buy_order_id == self.buy_order.id
        assert trade.sell_order_id == self.sell_order.id

    def test_trade_settlement_validation(self):
        """测试交易结算验证."""
        # 测试基础资产数量必须大于0
        with pytest.raises(ValidationError):
            TradeSettlement(
                buy_order=self.buy_order,
                sell_order=self.sell_order,
                trading_pair=TradingPairType.BTC_USDT,
                base_amount=0,
                price=50000.0,
            )

        # 测试价格必须大于0
        with pytest.raises(ValidationError):
            TradeSettlement(
                buy_order=self.buy_order,
                sell_order=self.sell_order,
                trading_pair=TradingPairType.BTC_USDT,
                base_amount=1.0,
                price=0,
            )

    def test_auto_generated_timestamp(self):
        """测试自动生成时间戳."""
        trade1 = TradeSettlement(
            buy_order=self.buy_order,
            sell_order=self.sell_order,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        trade2 = TradeSettlement(
            buy_order=self.buy_order,
            sell_order=self.sell_order,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        assert trade1.timestamp != trade2.timestamp

    def test_trade_settlement_minimum_amount(self):
        """测试交易结算最小数量."""
        # 测试极小的交易数量
        trade = TradeSettlement(
            buy_order=self.buy_order,
            sell_order=self.sell_order,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=0.000001,
            price=50000.0,
        )
        assert trade.base_amount == 0.000001

    def test_trade_settlement_high_price(self):
        """测试交易结算高价格."""
        trade = TradeSettlement(
            buy_order=self.buy_order,
            sell_order=self.sell_order,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=999999.99,
        )
        assert trade.price == 999999.99
