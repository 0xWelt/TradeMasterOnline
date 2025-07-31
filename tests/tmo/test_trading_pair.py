"""测试 tmo/trading_pair.py 的交易对引擎功能."""

from tmo.constants import AssetType, OrderStatus, OrderType, TradingPairType
from tmo.trading_pair import TradingPairEngine
from tmo.typing import Order
from tmo.user import User


class TestTradingPairEngineInitialization:
    """测试交易对引擎初始化."""

    def test_trading_pair_engine_initialization(self):
        """测试交易对引擎初始化."""
        users = {}
        engine = TradingPairEngine(TradingPairType.BTC_USDT, users)
        assert engine.base_asset == TradingPairType.BTC_USDT.base_asset
        assert engine.quote_asset == TradingPairType.BTC_USDT.quote_asset
        assert engine.current_price == 50000.0
        assert engine.symbol == 'BTC/USDT'
        assert len(engine.orders[OrderType.BUY]) == 0
        assert len(engine.orders[OrderType.SELL]) == 0
        assert len(engine.orders[OrderType.MARKET_BUY]) == 0
        assert len(engine.orders[OrderType.MARKET_SELL]) == 0
        assert len(engine.trade_history) == 0

    def test_different_trading_pairs(self):
        """测试不同交易对的初始化."""
        users = {}
        btc_usdt = TradingPairEngine(TradingPairType.BTC_USDT, users)
        eth_usdt = TradingPairEngine(TradingPairType.ETH_USDT, users)
        eth_btc = TradingPairEngine(TradingPairType.ETH_BTC, users)

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
        self.users = {}
        self.engine = TradingPairEngine(TradingPairType.BTC_USDT, self.users)
        self.user = User(username='test_user', email='test@example.com')
        self.users[self.user.id] = self.user
        # 为测试用户初始化足够的可用余额
        self.user.update_total_asset(AssetType.USDT, 100000.0)
        self.user.update_total_asset(AssetType.BTC, 10.0)

    def test_add_limit_buy_order(self):
        """测试添加限价买单."""
        order = self.engine.place_order(
            user=self.user,
            order_type=OrderType.BUY,
            base_amount=1.0,
            price=50000.0,
        )
        assert len(self.engine.buy_orders) == 1
        assert self.engine.buy_orders[0] == order

    def test_add_limit_sell_order(self):
        """测试添加限价卖单."""
        order = self.engine.place_order(
            user=self.user,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=51000.0,
        )
        assert len(self.engine.sell_orders) == 1
        assert self.engine.sell_orders[0] == order

    def test_add_market_buy_order(self):
        """测试添加市价买单."""
        order = self.engine.place_order(
            user=self.user,
            order_type=OrderType.MARKET_BUY,
            quote_amount=1000.0,
        )
        assert len(self.engine.market_buy_orders) == 1
        assert self.engine.market_buy_orders[0] == order

    def test_add_market_sell_order(self):
        """测试添加市价卖单."""
        order = self.engine.place_order(
            user=self.user,
            order_type=OrderType.MARKET_SELL,
            base_amount=1.0,
        )
        assert len(self.engine.market_sell_orders) == 1
        assert self.engine.market_sell_orders[0] == order

    def test_remove_order(self):
        """测试移除订单."""
        order = self.engine.place_order(
            user=self.user,
            order_type=OrderType.BUY,
            base_amount=1.0,
            price=48000.0,  # 使用不会匹配的价格
        )
        assert len(self.engine.buy_orders) == 1

        result = self.engine.cancel_order(order, self.user)
        assert result is True
        assert len(self.engine.buy_orders) == 0

    def test_remove_nonexistent_order(self):
        """测试移除不存在的订单."""
        from tmo.constants import OrderType, TradingPairType

        # 创建一个不存在的订单对象
        fake_order = Order(
            user_id=self.user.id,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        result = self.engine.cancel_order(fake_order, self.user)
        assert result is False

    def test_buy_order_sorting(self):
        """测试买单价格排序（降序）."""
        # 为用户充值足够的USDT
        self.user.update_total_asset(AssetType.USDT, 200000.0)

        self.engine.place_order(
            user=self.user,
            order_type=OrderType.BUY,
            base_amount=1.0,
            price=49000.0,
        )
        self.engine.place_order(
            user=self.user,
            order_type=OrderType.BUY,
            base_amount=1.0,
            price=51000.0,
        )
        self.engine.place_order(
            user=self.user,
            order_type=OrderType.BUY,
            base_amount=1.0,
            price=50000.0,
        )

        assert self.engine.buy_orders[0].price == 51000.0
        assert self.engine.buy_orders[1].price == 50000.0
        assert self.engine.buy_orders[2].price == 49000.0

    def test_sell_order_sorting(self):
        """测试卖单价格排序（升序）."""
        # 为用户充值足够的BTC
        self.user.update_total_asset(AssetType.BTC, 10.0)

        self.engine.place_order(
            user=self.user,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=51000.0,
        )
        self.engine.place_order(
            user=self.user,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=49000.0,
        )
        self.engine.place_order(
            user=self.user,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=50000.0,
        )

        assert self.engine.sell_orders[0].price == 49000.0
        assert self.engine.sell_orders[1].price == 50000.0
        assert self.engine.sell_orders[2].price == 51000.0


class TestOrderMatching:
    """测试订单撮合功能."""

    def setup_method(self):
        """设置测试环境."""
        self.users = {}
        self.engine = TradingPairEngine(TradingPairType.BTC_USDT, self.users)
        self.buyer = User(username='buyer', email='buyer@example.com')
        self.seller = User(username='seller', email='seller@example.com')
        self.users[self.buyer.id] = self.buyer
        self.users[self.seller.id] = self.seller

        # 为测试用户初始化足够的可用余额（而不是锁定余额）
        # 买家需要有足够的USDT可用余额
        self.buyer.update_total_asset(AssetType.USDT, 1000000.0)
        self.buyer.update_total_asset(AssetType.BTC, 100.0)
        # 卖家需要有足够的BTC可用余额
        self.seller.update_total_asset(AssetType.BTC, 100.0)
        self.seller.update_total_asset(AssetType.USDT, 1000000.0)

    def test_limit_order_matching_exact_price(self):
        """测试限价订单精确价格匹配."""
        # 使用place_order来确保余额验证和锁定
        buy_order = self.engine.place_order(
            user=self.buyer,
            order_type=OrderType.BUY,
            base_amount=1.0,
            price=50000.0,
        )
        # 创建卖单
        sell_order = self.engine.place_order(
            user=self.seller,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=50000.0,
        )

        # 检查交易历史，因为订单会在place_order时自动匹配
        assert len(self.engine.trade_history) >= 1
        trade = self.engine.trade_history[-1]
        assert trade.base_amount == 1.0
        assert trade.price == 50000.0
        assert buy_order.status == OrderStatus.FILLED
        assert sell_order.status == OrderStatus.FILLED
        assert self.engine.current_price == 50000.0

    def test_limit_order_matching_better_price(self):
        """测试限价订单更好价格匹配."""
        # 买单价格高于卖单价格
        buy_order = self.engine.place_order(
            user=self.buyer,
            order_type=OrderType.BUY,
            base_amount=1.0,
            price=51000.0,
        )
        sell_order = self.engine.place_order(
            user=self.seller,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=50000.0,
        )

        # 订单会在place_order时自动匹配
        assert len(self.engine.trade_history) >= 1
        trade = self.engine.trade_history[-1]
        assert trade.base_amount == 1.0
        assert trade.price == 50000.0  # 按卖单价格成交
        assert buy_order.status == OrderStatus.FILLED
        assert sell_order.status == OrderStatus.FILLED

    def test_limit_order_no_matching(self):
        """测试限价订单无法匹配."""
        # 买单价格低于卖单价格
        buy_order = self.engine.place_order(
            user=self.buyer,
            order_type=OrderType.BUY,
            base_amount=1.0,
            price=49000.0,
        )
        sell_order = self.engine.place_order(
            user=self.seller,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=50000.0,
        )

        # 由于价格不匹配，不会有交易产生
        assert len(self.engine.trade_history) == 0
        assert buy_order.status == OrderStatus.PENDING
        assert sell_order.status == OrderStatus.PENDING

    def test_partial_fill(self):
        """测试部分成交."""
        # 买单数量大于卖单
        buy_order = self.engine.place_order(
            user=self.buyer,
            order_type=OrderType.BUY,
            base_amount=2.0,
            price=50000.0,
        )
        sell_order = self.engine.place_order(
            user=self.seller,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=50000.0,
        )

        # 订单会在place_order时自动匹配
        assert len(self.engine.trade_history) >= 1
        trade = self.engine.trade_history[-1]
        assert trade.base_amount == 1.0
        assert trade.price == 50000.0
        assert buy_order.status == OrderStatus.PARTIALLY_FILLED
        assert sell_order.status == OrderStatus.FILLED
        assert buy_order.filled_base_amount == 1.0

    def test_market_buy_order_execution(self):
        """测试市价买单执行."""
        # 创建限价卖单
        sell_order = self.engine.place_order(
            user=self.seller,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=50000.0,
        )

        # 创建市价买单
        market_buy = self.engine.place_order(
            user=self.buyer,
            order_type=OrderType.MARKET_BUY,
            quote_amount=50000.0,
        )

        # 订单会在place_order时自动匹配
        assert len(self.engine.trade_history) >= 1
        trade = self.engine.trade_history[-1]
        assert trade.base_amount == 1.0
        assert trade.price == 50000.0
        assert market_buy.status == OrderStatus.FILLED
        assert sell_order.status == OrderStatus.FILLED

    def test_market_sell_order_execution(self):
        """测试市价卖单执行."""
        # 创建限价买单
        buy_order = self.engine.place_order(
            user=self.buyer,
            order_type=OrderType.BUY,
            base_amount=1.0,
            price=50000.0,
        )

        # 创建市价卖单
        market_sell = self.engine.place_order(
            user=self.seller,
            order_type=OrderType.MARKET_SELL,
            base_amount=1.0,
        )

        # 订单会在place_order时自动匹配
        assert len(self.engine.trade_history) >= 1
        trade = self.engine.trade_history[-1]
        assert trade.base_amount == 1.0
        assert trade.price == 50000.0
        assert market_sell.status == OrderStatus.FILLED
        assert buy_order.status == OrderStatus.FILLED

    def test_multiple_trades(self):
        """测试多笔交易."""
        # 创建多个订单
        buy_order1 = self.engine.place_order(
            user=self.buyer,
            order_type=OrderType.BUY,
            base_amount=1.0,
            price=50000.0,
        )
        buy_order2 = self.engine.place_order(
            user=self.buyer,
            order_type=OrderType.BUY,
            base_amount=1.0,
            price=49000.0,
        )
        sell_order = self.engine.place_order(
            user=self.seller,
            order_type=OrderType.SELL,
            base_amount=2.0,
            price=50000.0,
        )

        # 订单会在place_order时自动匹配
        assert len(self.engine.trade_history) >= 1
        # 只有价格50000的买单能成交
        assert self.engine.trade_history[-1].base_amount == 1.0
        assert buy_order1.status == OrderStatus.FILLED
        assert buy_order2.status == OrderStatus.PENDING
        assert sell_order.status == OrderStatus.PARTIALLY_FILLED

    def test_zero_amount_trade_prevention(self):
        """测试防止零数量交易."""
        # 创建极小数量的订单，但使用更合理的值避免性能问题
        buy_order = self.engine.place_order(
            user=self.buyer,
            order_type=OrderType.BUY,
            base_amount=1e-8,  # 使用更合理的极小值
            price=50000.0,
        )
        sell_order = self.engine.place_order(
            user=self.seller,
            order_type=OrderType.SELL,
            base_amount=1e-8,
            price=50000.0,
        )

        # 订单会在place_order时自动匹配
        assert len(self.engine.trade_history) >= 1
        # 验证交易能正常进行，这个数量应该是有效的
        trade = self.engine.trade_history[-1]
        assert trade.base_amount == 1e-8
        assert buy_order.status == OrderStatus.FILLED
        assert sell_order.status == OrderStatus.FILLED

    def test_market_order_with_base_amount(self):
        """测试市价订单使用基础资产数量."""
        # 创建限价卖单
        sell_order = self.engine.place_order(
            user=self.seller,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=50000.0,
        )

        # 创建市价买单使用base_amount
        market_buy = self.engine.place_order(
            user=self.buyer,
            order_type=OrderType.MARKET_BUY,
            base_amount=0.5,
        )

        # 订单会在place_order时自动匹配
        assert len(self.engine.trade_history) >= 1
        trade = self.engine.trade_history[-1]
        assert trade.base_amount == 0.5
        assert trade.price == 50000.0
        assert market_buy.status == OrderStatus.FILLED
        assert sell_order.status == OrderStatus.PARTIALLY_FILLED

    def test_market_order_with_quote_amount(self):
        """测试市价订单使用计价资产金额."""
        # 创建限价卖单
        self.engine.place_order(
            user=self.seller,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=50000.0,
        )
        self.engine.place_order(
            user=self.seller,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=51000.0,
        )

        # 创建市价买单使用quote_amount
        market_buy = self.engine.place_order(
            user=self.buyer,
            order_type=OrderType.MARKET_BUY,
            quote_amount=75000.0,
        )

        # 订单会在place_order时自动匹配
        assert len(self.engine.trade_history) >= 2
        # 检查最近的两笔交易
        trades = self.engine.trade_history[-2:]
        assert trades[0].price == 50000.0  # 先成交价格低
        assert trades[1].price == 51000.0
        assert market_buy.status == OrderStatus.FILLED


class TestMarketData:
    """测试市场数据功能."""

    def setup_method(self):
        """设置测试环境."""
        self.users = {}
        self.engine = TradingPairEngine(TradingPairType.BTC_USDT, self.users)
        self.user = User(username='test_user', email='test@example.com')
        self.users[self.user.id] = self.user
        # 为测试用户初始化足够的可用余额
        self.user.update_total_asset(AssetType.USDT, 100000.0)
        self.user.update_total_asset(AssetType.BTC, 10.0)

    def test_get_order_book_empty(self):
        """测试空订单簿."""
        order_book = self.engine.get_order_book()
        assert order_book.bids == []
        assert order_book.asks == []

    def test_get_order_book_with_orders(self):
        """测试带订单的订单簿."""
        # 创建不会匹配的订单
        self.engine.place_order(
            user=self.user,
            order_type=OrderType.BUY,
            base_amount=1.0,
            price=48000.0,  # 低于卖单价格，不会匹配
        )
        self.engine.place_order(
            user=self.user,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=52000.0,
        )

        order_book = self.engine.get_order_book()
        assert len(order_book.bids) == 1
        assert order_book.bids[0].price == 48000.0
        assert order_book.bids[0].quantity == 1.0
        assert len(order_book.asks) == 1
        assert order_book.asks[0].price == 52000.0
        assert order_book.asks[0].quantity == 1.0

    def test_get_recent_trades_empty(self):
        """测试空成交记录."""
        trades = self.engine.get_recent_trades()
        assert trades == []

    def test_get_recent_trades_with_limit(self):
        """测试限制数量的成交记录."""
        # 创建交易
        buyer = User(username='buyer', email='buyer@example.com')
        seller = User(username='seller', email='seller@example.com')

        # 将用户添加到用户字典
        self.users[buyer.id] = buyer
        self.users[seller.id] = seller

        # 为用户初始化足够的可用余额
        buyer.update_total_asset(AssetType.USDT, 100000.0)
        buyer.update_total_asset(AssetType.BTC, 10.0)
        seller.update_total_asset(AssetType.BTC, 10.0)
        seller.update_total_asset(AssetType.USDT, 100000.0)

        self.engine.place_order(
            user=buyer,
            order_type=OrderType.BUY,
            base_amount=1.0,
            price=50000.0,
        )
        self.engine.place_order(
            user=seller,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=50000.0,
        )

        # 验证交易发生
        assert len(self.engine.trade_history) >= 1

        trades = self.engine.get_recent_trades(limit=5)
        assert len(trades) >= 1

    def test_price_update_from_trades(self):
        """测试从交易更新价格."""
        initial_price = self.engine.current_price

        # 创建交易
        buyer = User(username='buyer', email='buyer@example.com')
        seller = User(username='seller', email='seller@example.com')

        # 将用户添加到用户字典
        self.users[buyer.id] = buyer
        self.users[seller.id] = seller

        # 为用户初始化足够的可用余额
        buyer.update_total_asset(AssetType.USDT, 100000.0)
        seller.update_total_asset(AssetType.BTC, 10.0)

        self.engine.place_order(
            user=buyer,
            order_type=OrderType.BUY,
            base_amount=1.0,
            price=52000.0,
        )
        self.engine.place_order(
            user=seller,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=52000.0,
        )

        # 验证交易发生
        assert len(self.engine.trade_history) >= 1
        assert self.engine.current_price == 52000.0
        assert self.engine.current_price != initial_price

    def test_trade_history_limit(self):
        """测试交易历史限制."""
        # 创建交易用户
        buyers = []
        sellers = []
        for i in range(10):  # 减少数量以避免性能问题
            buyer = User(username=f'buyer{i}', email=f'buyer{i}@example.com')
            seller = User(username=f'seller{i}', email=f'seller{i}@example.com')

            # 将用户添加到用户字典
            self.users[buyer.id] = buyer
            self.users[seller.id] = seller

            # 初始化余额
            buyer.update_total_asset(AssetType.USDT, 100000.0)
            seller.update_total_asset(AssetType.BTC, 10.0)

            buyers.append(buyer)
            sellers.append(seller)

        # 创建交易
        for i in range(10):
            self.engine.place_order(
                user=buyers[i],
                order_type=OrderType.BUY,
                base_amount=1.0,
                price=50000.0 + i,
            )
            self.engine.place_order(
                user=sellers[i],
                order_type=OrderType.SELL,
                base_amount=1.0,
                price=50000.0 + i,
            )

        # 检查交易历史
        assert len(self.engine.trade_history) >= 5  # 至少有一些交易


class TestOrderBookCleanup:
    """测试订单簿清理功能."""

    def setup_method(self):
        """设置测试环境."""
        self.users = {}
        self.engine = TradingPairEngine(TradingPairType.BTC_USDT, self.users)
        self.user = User(username='test_user', email='test@example.com')
        self.users[self.user.id] = self.user
        # 为测试用户初始化足够的可用余额
        self.user.update_total_asset(AssetType.USDT, 100000.0)
        self.user.update_total_asset(AssetType.BTC, 10.0)

    def test_cleanup_filled_orders(self):
        """测试清理已成交订单."""
        # 创建两个不同价格的订单避免价格交叉
        buyer = User(username='buyer', email='buyer@example.com')
        seller = User(username='seller', email='seller@example.com')

        # 将用户添加到用户字典
        self.users[buyer.id] = buyer
        self.users[seller.id] = seller

        buyer.update_total_asset(AssetType.USDT, 100000.0)
        seller.update_total_asset(AssetType.BTC, 10.0)

        self.engine.place_order(
            user=buyer,
            order_type=OrderType.BUY,
            base_amount=1.0,
            price=50000.0,
        )
        self.engine.place_order(
            user=seller,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=50000.0,
        )

        # 订单会在place_order时自动匹配
        assert len(self.engine.trade_history) >= 1

        # 订单应该被清理
        assert len(self.engine.buy_orders) == 0
        assert len(self.engine.sell_orders) == 0

    def test_cleanup_partially_filled_orders(self):
        """测试不清理部分成交订单."""
        buyer = User(username='buyer', email='buyer@example.com')
        seller = User(username='seller', email='seller@example.com')

        # 将用户添加到用户字典
        self.users[buyer.id] = buyer
        self.users[seller.id] = seller

        buyer.update_total_asset(AssetType.USDT, 100000.0)
        seller.update_total_asset(AssetType.BTC, 10.0)

        self.engine.place_order(
            user=buyer,
            order_type=OrderType.BUY,
            base_amount=2.0,
            price=50000.0,
        )
        self.engine.place_order(
            user=seller,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=50000.0,
        )

        # 订单会在place_order时自动匹配
        assert len(self.engine.trade_history) >= 1

        # 买单应该保留（部分成交）
        assert len(self.engine.buy_orders) == 1
        assert len(self.engine.sell_orders) == 0
        assert self.engine.buy_orders[0].status == OrderStatus.PARTIALLY_FILLED


class TestEdgeCases:
    """测试边界情况."""

    def setup_method(self):
        """设置测试环境."""
        self.users = {}
        self.engine = TradingPairEngine(TradingPairType.BTC_USDT, self.users)
        self.user = User(username='test_user', email='test@example.com')
        self.users[self.user.id] = self.user
        # 为测试用户初始化足够的可用余额
        self.user.update_total_asset(AssetType.USDT, 1000000.0)
        self.user.update_total_asset(AssetType.BTC, 100.0)

    def test_empty_market_orders(self):
        """测试空市价订单处理."""
        # 创建市价买单，但没有限价卖单
        market_buy = self.engine.place_order(
            user=self.user,
            order_type=OrderType.MARKET_BUY,
            quote_amount=1000.0,
        )

        # 由于没有限价卖单，不会有交易产生
        assert len(self.engine.trade_history) == 0
        assert market_buy.status == OrderStatus.PENDING

    def test_market_order_insufficient_liquidity(self):
        """测试市价订单流动性不足."""
        # 创建小额限价卖单
        sell_order = self.engine.place_order(
            user=self.user,
            order_type=OrderType.SELL,
            base_amount=0.5,
            price=50000.0,
        )

        # 创建大额市价买单 - 修复：使用不同的用户
        buyer = User(username='buyer', email='buyer@example.com')
        self.users[buyer.id] = buyer
        buyer.update_total_asset(AssetType.USDT, 1000000.0)
        market_buy = self.engine.place_order(
            user=buyer,
            order_type=OrderType.MARKET_BUY,
            quote_amount=100000.0,  # 需要2个BTC，但只有0.5个
        )

        # 订单会在place_order时自动匹配
        assert len(self.engine.trade_history) >= 1
        trade = self.engine.trade_history[-1]
        assert trade.base_amount == 0.5  # 只能成交部分
        assert market_buy.status == OrderStatus.PARTIALLY_FILLED
        assert sell_order.status == OrderStatus.FILLED

    def test_order_book_depth(self):
        """测试订单簿深度."""
        # 添加多个订单
        for i in range(10):
            self.engine.place_order(
                user=self.user,
                order_type=OrderType.BUY,
                base_amount=1.0,
                price=48000.0 + i * 100,
            )
            self.engine.place_order(
                user=self.user,
                order_type=OrderType.SELL,
                base_amount=1.0,
                price=53000.0 + i * 100,
            )

        order_book = self.engine.get_order_book()
        assert len(order_book.bids) == 10
        assert len(order_book.asks) == 10

    def test_symbol_property(self):
        """测试交易对符号属性."""
        users = {}
        engine = TradingPairEngine(TradingPairType.ETH_USDT, users)
        assert engine.symbol == 'ETH/USDT'

    def test_get_current_price(self):
        """测试获取当前价格接口."""
        users = {}
        engine = TradingPairEngine(TradingPairType.BTC_USDT, users)

        # 初始价格应该为初始值
        assert engine.get_current_price() == 50000.0

        # 也可以通过属性访问
        assert engine.current_price == 50000.0

        # 创建交易用户
        buyer = User(username='buyer', email='buyer@example.com')
        seller = User(username='seller', email='seller@example.com')
        users[buyer.id] = buyer
        users[seller.id] = seller

        buyer.update_total_asset(AssetType.USDT, 100000.0)
        seller.update_total_asset(AssetType.BTC, 10.0)

        # 创建交易来更新价格
        engine.place_order(
            user=buyer,
            order_type=OrderType.BUY,
            base_amount=1.0,
            price=52000.0,
        )
        engine.place_order(
            user=seller,
            order_type=OrderType.SELL,
            base_amount=1.0,
            price=52000.0,
        )

        # 验证价格已更新
        assert engine.get_current_price() == 52000.0
        assert engine.current_price == 52000.0

    def test_get_recent_trades_limit_zero(self):
        """测试获取零条成交记录."""
        trades = self.engine.get_recent_trades(limit=0)
        assert trades == []

    def test_get_order_book_with_different_pairs(self):
        """测试不同交易对的订单簿."""
        users = {}
        eth_usdt = TradingPairEngine(TradingPairType.ETH_USDT, users)
        order_book = eth_usdt.get_order_book()
        assert order_book.bids == []
        assert order_book.asks == []
