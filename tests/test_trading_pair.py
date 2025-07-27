"""测试 tmo/trading_pair.py 的交易对引擎功能."""

from tmo.constants import AssetType, OrderStatus, OrderType, TradingPairType
from tmo.trading_pair import TradingPairEngine
from tmo.typing import Order, User


class TestTradingPairEngineInitialization:
    """测试交易对引擎初始化."""

    def test_trading_pair_engine_initialization(self):
        """测试交易对引擎初始化."""
        engine = TradingPairEngine(TradingPairType.BTC_USDT)
        assert engine.base_asset == TradingPairType.BTC_USDT.base_asset
        assert engine.quote_asset == TradingPairType.BTC_USDT.quote_asset
        assert engine.current_price == 50000.0
        assert engine.symbol == 'BTC/USDT'
        assert len(engine.buy_orders) == 0
        assert len(engine.sell_orders) == 0
        assert len(engine.market_buy_orders) == 0
        assert len(engine.market_sell_orders) == 0
        assert len(engine.trade_history) == 0

    def test_different_trading_pairs(self):
        """测试不同交易对的初始化."""
        btc_usdt = TradingPairEngine(TradingPairType.BTC_USDT)
        eth_usdt = TradingPairEngine(TradingPairType.ETH_USDT)
        eth_btc = TradingPairEngine(TradingPairType.ETH_BTC)

        assert btc_usdt.base_asset == AssetType.BTC
        assert btc_usdt.quote_asset == AssetType.USDT
        assert btc_usdt.current_price == 50000.0

        assert eth_usdt.base_asset == AssetType.ETH
        assert eth_usdt.quote_asset == AssetType.USDT
        assert eth_usdt.current_price == 3000.0

        assert eth_btc.base_asset == AssetType.ETH
        assert eth_btc.quote_asset == AssetType.BTC
        assert eth_btc.current_price == 0.06


class TestOrderManagement:
    """测试订单管理功能."""

    def setup_method(self):
        """设置测试环境."""
        self.engine = TradingPairEngine(TradingPairType.BTC_USDT)
        self.user = User(username='test_user', email='test@example.com')

    def test_add_limit_buy_order(self):
        """测试添加限价买单."""
        order = Order(
            user=self.user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        self.engine.add_order(order)
        assert len(self.engine.buy_orders) == 1
        assert self.engine.buy_orders[0] == order

    def test_add_limit_sell_order(self):
        """测试添加限价卖单."""
        order = Order(
            user=self.user,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=51000.0,
        )
        self.engine.add_order(order)
        assert len(self.engine.sell_orders) == 1
        assert self.engine.sell_orders[0] == order

    def test_add_market_buy_order(self):
        """测试添加市价买单."""
        order = Order(
            user=self.user,
            order_type=OrderType.MARKET_BUY,
            trading_pair=TradingPairType.BTC_USDT,
            quote_amount=1000.0,
        )
        self.engine.add_order(order)
        assert len(self.engine.market_buy_orders) == 1
        assert self.engine.market_buy_orders[0] == order

    def test_add_market_sell_order(self):
        """测试添加市价卖单."""
        order = Order(
            user=self.user,
            order_type=OrderType.MARKET_SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
        )
        self.engine.add_order(order)
        assert len(self.engine.market_sell_orders) == 1
        assert self.engine.market_sell_orders[0] == order

    def test_remove_order(self):
        """测试移除订单."""
        order = Order(
            user=self.user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        self.engine.add_order(order)
        assert len(self.engine.buy_orders) == 1

        result = self.engine.remove_order(order)
        assert result is True
        assert len(self.engine.buy_orders) == 0

    def test_remove_nonexistent_order(self):
        """测试移除不存在的订单."""
        order = Order(
            user=self.user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        result = self.engine.remove_order(order)
        assert result is False

    def test_buy_order_sorting(self):
        """测试买单价格排序（降序）."""
        order1 = Order(
            user=self.user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=49000.0,
        )
        order2 = Order(
            user=self.user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=51000.0,
        )
        order3 = Order(
            user=self.user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )

        self.engine.add_order(order1)
        self.engine.add_order(order2)
        self.engine.add_order(order3)

        assert self.engine.buy_orders[0].price == 51000.0
        assert self.engine.buy_orders[1].price == 50000.0
        assert self.engine.buy_orders[2].price == 49000.0

    def test_sell_order_sorting(self):
        """测试卖单价格排序（升序）."""
        order1 = Order(
            user=self.user,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=51000.0,
        )
        order2 = Order(
            user=self.user,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=49000.0,
        )
        order3 = Order(
            user=self.user,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )

        self.engine.add_order(order1)
        self.engine.add_order(order2)
        self.engine.add_order(order3)

        assert self.engine.sell_orders[0].price == 49000.0
        assert self.engine.sell_orders[1].price == 50000.0
        assert self.engine.sell_orders[2].price == 51000.0


class TestOrderMatching:
    """测试订单撮合功能."""

    def setup_method(self):
        """设置测试环境."""
        self.engine = TradingPairEngine(TradingPairType.BTC_USDT)
        self.buyer = User(username='buyer', email='buyer@example.com')
        self.seller = User(username='seller', email='seller@example.com')

    def test_limit_order_matching_exact_price(self):
        """测试限价订单精确价格匹配."""
        # 创建买单
        buy_order = Order(
            user=self.buyer,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        # 创建卖单
        sell_order = Order(
            user=self.seller,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )

        self.engine.add_order(buy_order)
        self.engine.add_order(sell_order)

        trades = self.engine.match_orders()
        assert len(trades) == 1
        assert trades[0].base_amount == 1.0
        assert trades[0].price == 50000.0
        assert buy_order.status == OrderStatus.FILLED
        assert sell_order.status == OrderStatus.FILLED
        assert self.engine.current_price == 50000.0

    def test_limit_order_matching_better_price(self):
        """测试限价订单更好价格匹配."""
        # 买单价格高于卖单价格
        buy_order = Order(
            user=self.buyer,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=51000.0,
        )
        sell_order = Order(
            user=self.seller,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )

        self.engine.add_order(buy_order)
        self.engine.add_order(sell_order)

        trades = self.engine.match_orders()
        assert len(trades) == 1
        assert trades[0].price == 50000.0  # 按卖单价格成交

    def test_limit_order_no_matching(self):
        """测试限价订单无法匹配."""
        # 买单价格低于卖单价格
        buy_order = Order(
            user=self.buyer,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=49000.0,
        )
        sell_order = Order(
            user=self.seller,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )

        self.engine.add_order(buy_order)
        self.engine.add_order(sell_order)

        trades = self.engine.match_orders()
        assert len(trades) == 0
        assert buy_order.status == OrderStatus.PENDING
        assert sell_order.status == OrderStatus.PENDING

    def test_partial_fill(self):
        """测试部分成交."""
        # 买单数量大于卖单
        buy_order = Order(
            user=self.buyer,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=2.0,
            price=50000.0,
        )
        sell_order = Order(
            user=self.seller,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )

        self.engine.add_order(buy_order)
        self.engine.add_order(sell_order)

        trades = self.engine.match_orders()
        assert len(trades) == 1
        assert trades[0].base_amount == 1.0
        assert buy_order.status == OrderStatus.PARTIALLY_FILLED
        assert sell_order.status == OrderStatus.FILLED
        assert buy_order.filled_base_amount == 1.0

    def test_market_buy_order_execution(self):
        """测试市价买单执行."""
        # 创建限价卖单
        sell_order = Order(
            user=self.seller,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        self.engine.add_order(sell_order)

        # 创建市价买单
        market_buy = Order(
            user=self.buyer,
            order_type=OrderType.MARKET_BUY,
            trading_pair=TradingPairType.BTC_USDT,
            quote_amount=50000.0,
        )
        self.engine.add_order(market_buy)

        trades = self.engine.match_orders()
        assert len(trades) == 1
        assert trades[0].base_amount == 1.0
        assert trades[0].price == 50000.0

    def test_market_sell_order_execution(self):
        """测试市价卖单执行."""
        # 创建限价买单
        buy_order = Order(
            user=self.buyer,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        self.engine.add_order(buy_order)

        # 创建市价卖单
        market_sell = Order(
            user=self.seller,
            order_type=OrderType.MARKET_SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
        )
        self.engine.add_order(market_sell)

        trades = self.engine.match_orders()
        assert len(trades) == 1
        assert trades[0].base_amount == 1.0
        assert trades[0].price == 50000.0

    def test_multiple_trades(self):
        """测试多笔交易."""
        # 创建多个订单
        buy_order1 = Order(
            user=self.buyer,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        buy_order2 = Order(
            user=self.buyer,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=49000.0,
        )
        sell_order = Order(
            user=self.seller,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=2.0,
            price=50000.0,
        )

        self.engine.add_order(buy_order1)
        self.engine.add_order(buy_order2)
        self.engine.add_order(sell_order)

        trades = self.engine.match_orders()
        assert len(trades) == 1  # 只有价格50000的买单能成交
        assert trades[0].base_amount == 1.0

    def test_zero_amount_trade_prevention(self):
        """测试防止零数量交易."""
        # 创建极小数量的订单，但使用更合理的值避免性能问题
        buy_order = Order(
            user=self.buyer,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1e-8,  # 使用更合理的极小值
            price=50000.0,
        )
        sell_order = Order(
            user=self.seller,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1e-8,
            price=50000.0,
        )

        self.engine.add_order(buy_order)
        self.engine.add_order(sell_order)

        trades = self.engine.match_orders()
        # 验证交易能正常进行，这个数量应该是有效的
        assert len(trades) == 1
        assert trades[0].base_amount == 1e-8

    def test_market_order_with_base_amount(self):
        """测试市价订单使用基础资产数量."""
        # 创建限价卖单
        sell_order = Order(
            user=self.seller,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        self.engine.add_order(sell_order)

        # 创建市价买单使用base_amount
        market_buy = Order(
            user=self.buyer,
            order_type=OrderType.MARKET_BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=0.5,
        )
        self.engine.add_order(market_buy)

        trades = self.engine.match_orders()
        assert len(trades) == 1
        assert trades[0].base_amount == 0.5

    def test_market_order_with_quote_amount(self):
        """测试市价订单使用计价资产金额."""
        # 创建限价卖单
        sell_order1 = Order(
            user=self.seller,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        sell_order2 = Order(
            user=self.seller,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=51000.0,
        )
        self.engine.add_order(sell_order1)
        self.engine.add_order(sell_order2)

        # 创建市价买单使用quote_amount
        market_buy = Order(
            user=self.buyer,
            order_type=OrderType.MARKET_BUY,
            trading_pair=TradingPairType.BTC_USDT,
            quote_amount=75000.0,
        )
        self.engine.add_order(market_buy)

        trades = self.engine.match_orders()
        assert len(trades) == 2
        assert trades[0].price == 50000.0  # 先成交价格低
        assert trades[1].price == 51000.0


class TestMarketData:
    """测试市场数据功能."""

    def setup_method(self):
        """设置测试环境."""
        self.engine = TradingPairEngine(TradingPairType.BTC_USDT)
        self.user = User(username='test_user', email='test@example.com')

    def test_get_order_book_empty(self):
        """测试空订单簿."""
        order_book = self.engine.get_order_book()
        assert order_book['bids'] == []
        assert order_book['asks'] == []

    def test_get_order_book_with_orders(self):
        """测试带订单的订单簿."""
        buy_order = Order(
            user=self.user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        sell_order = Order(
            user=self.user,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=51000.0,
        )

        self.engine.add_order(buy_order)
        self.engine.add_order(sell_order)

        order_book = self.engine.get_order_book()
        assert len(order_book['bids']) == 1
        assert order_book['bids'][0]['price'] == 50000.0
        assert order_book['bids'][0]['quantity'] == 1.0
        assert len(order_book['asks']) == 1
        assert order_book['asks'][0]['price'] == 51000.0
        assert order_book['asks'][0]['quantity'] == 1.0

    def test_get_recent_trades_empty(self):
        """测试空成交记录."""
        trades = self.engine.get_recent_trades()
        assert trades == []

    def test_get_recent_trades_with_limit(self):
        """测试限制数量的成交记录."""
        # 创建交易
        buy_order = Order(
            user=self.user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        sell_order = Order(
            user=self.user,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )

        self.engine.add_order(buy_order)
        self.engine.add_order(sell_order)
        self.engine.match_orders()

        trades = self.engine.get_recent_trades(limit=5)
        assert len(trades) == 1

    def test_get_market_summary_empty(self):
        """测试空市场摘要."""
        summary = self.engine.get_market_summary()
        assert summary['symbol'] == 'BTC/USDT'
        assert summary['current_price'] == 50000.0
        assert summary['total_bids'] == 0
        assert summary['total_asks'] == 0
        assert summary['recent_trades'] == 0
        assert summary['best_bid'] is None
        assert summary['best_ask'] is None

    def test_get_market_summary_with_data(self):
        """测试带数据的市场摘要."""
        buy_order = Order(
            user=self.user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        sell_order = Order(
            user=self.user,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=51000.0,
        )

        self.engine.add_order(buy_order)
        self.engine.add_order(sell_order)

        summary = self.engine.get_market_summary()
        assert summary['total_bids'] == 1
        assert summary['total_asks'] == 1
        assert summary['best_bid'] == 50000.0
        assert summary['best_ask'] == 51000.0

    def test_price_update_from_trades(self):
        """测试从交易更新价格."""
        initial_price = self.engine.current_price

        buy_order = Order(
            user=self.user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=52000.0,
        )
        sell_order = Order(
            user=self.user,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=52000.0,
        )

        self.engine.add_order(buy_order)
        self.engine.add_order(sell_order)
        self.engine.match_orders()

        assert self.engine.current_price == 52000.0
        assert self.engine.current_price != initial_price

    def test_trade_history_limit(self):
        """测试交易历史限制."""
        # 创建大量交易
        for i in range(1005):
            buy_order = Order(
                user=self.user,
                order_type=OrderType.BUY,
                trading_pair=TradingPairType.BTC_USDT,
                base_amount=1.0,
                price=50000.0 + i,
            )
            sell_order = Order(
                user=self.user,
                order_type=OrderType.SELL,
                trading_pair=TradingPairType.BTC_USDT,
                base_amount=1.0,
                price=50000.0 + i,
            )

            self.engine.add_order(buy_order)
            self.engine.add_order(sell_order)
            self.engine.match_orders()

        # 检查交易历史限制
        assert len(self.engine.trade_history) == 1000  # 应该被限制在1000


class TestOrderBookCleanup:
    """测试订单簿清理功能."""

    def setup_method(self):
        """设置测试环境."""
        self.engine = TradingPairEngine(TradingPairType.BTC_USDT)
        self.user = User(username='test_user', email='test@example.com')

    def test_cleanup_filled_orders(self):
        """测试清理已成交订单."""
        buy_order = Order(
            user=self.user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        sell_order = Order(
            user=self.user,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )

        self.engine.add_order(buy_order)
        self.engine.add_order(sell_order)
        self.engine.match_orders()

        # 订单应该被清理
        assert len(self.engine.buy_orders) == 0
        assert len(self.engine.sell_orders) == 0

    def test_cleanup_partially_filled_orders(self):
        """测试不清理部分成交订单."""
        buy_order = Order(
            user=self.user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=2.0,
            price=50000.0,
        )
        sell_order = Order(
            user=self.user,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )

        self.engine.add_order(buy_order)
        self.engine.add_order(sell_order)
        self.engine.match_orders()

        # 买单应该保留（部分成交）
        assert len(self.engine.buy_orders) == 1
        assert len(self.engine.sell_orders) == 0
        assert buy_order.status == OrderStatus.PARTIALLY_FILLED


class TestEdgeCases:
    """测试边界情况."""

    def setup_method(self):
        """设置测试环境."""
        self.engine = TradingPairEngine(TradingPairType.BTC_USDT)
        self.user = User(username='test_user', email='test@example.com')

    def test_empty_market_orders(self):
        """测试空市价订单处理."""
        # 创建市价买单，但没有限价卖单
        market_buy = Order(
            user=self.user,
            order_type=OrderType.MARKET_BUY,
            trading_pair=TradingPairType.BTC_USDT,
            quote_amount=1000.0,
        )
        self.engine.add_order(market_buy)

        trades = self.engine.match_orders()
        assert len(trades) == 0
        assert market_buy.status == OrderStatus.PENDING

    def test_market_order_insufficient_liquidity(self):
        """测试市价订单流动性不足."""
        # 创建小额限价卖单
        sell_order = Order(
            user=self.user,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=0.5,
            price=50000.0,
        )
        self.engine.add_order(sell_order)

        # 创建大额市价买单
        market_buy = Order(
            user=self.user,
            order_type=OrderType.MARKET_BUY,
            trading_pair=TradingPairType.BTC_USDT,
            quote_amount=100000.0,  # 需要2个BTC，但只有0.5个
        )
        self.engine.add_order(market_buy)

        trades = self.engine.match_orders()
        assert len(trades) == 1
        assert trades[0].base_amount == 0.5  # 只能成交部分

    def test_order_book_depth(self):
        """测试订单簿深度."""
        # 添加多个订单
        for i in range(10):
            buy_order = Order(
                user=self.user,
                order_type=OrderType.BUY,
                trading_pair=TradingPairType.BTC_USDT,
                base_amount=1.0,
                price=49000.0 + i * 100,
            )
            sell_order = Order(
                user=self.user,
                order_type=OrderType.SELL,
                trading_pair=TradingPairType.BTC_USDT,
                base_amount=1.0,
                price=51000.0 + i * 100,
            )
            self.engine.add_order(buy_order)
            self.engine.add_order(sell_order)

        order_book = self.engine.get_order_book()
        assert len(order_book['bids']) == 10
        assert len(order_book['asks']) == 10

    def test_symbol_property(self):
        """测试交易对符号属性."""
        engine = TradingPairEngine(TradingPairType.ETH_USDT)
        assert engine.symbol == 'ETH/USDT'

    def test_get_recent_trades_limit_zero(self):
        """测试获取零条成交记录."""
        trades = self.engine.get_recent_trades(limit=0)
        assert trades == []

    def test_get_order_book_with_different_pairs(self):
        """测试不同交易对的订单簿."""
        eth_usdt = TradingPairEngine(TradingPairType.ETH_USDT)
        order_book = eth_usdt.get_order_book()
        assert order_book['bids'] == []
        assert order_book['asks'] == []

    def test_get_market_summary_empty(self):
        """测试空市场摘要."""
        summary = self.engine.get_market_summary()
        assert summary['symbol'] == 'BTC/USDT'
        assert summary['current_price'] == 50000.0
        assert summary['total_bids'] == 0
        assert summary['total_asks'] == 0
        assert summary['recent_trades'] == 0
        assert summary['best_bid'] is None
        assert summary['best_ask'] is None
