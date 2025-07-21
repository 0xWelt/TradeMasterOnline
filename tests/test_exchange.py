"""测试交易所核心逻辑"""

import pytest

from tmo.exchange import Exchange
from tmo.typing import AssetType, OrderType


class TestExchange:
    """测试交易所类"""

    @pytest.fixture
    def exchange(self) -> Exchange:
        """创建交易所实例"""
        return Exchange()

    def test_exchange_initialization(self, exchange: Exchange) -> None:
        """测试交易所初始化"""
        # 检查资产
        assert AssetType.USDT in exchange.assets
        assert AssetType.BTC in exchange.assets
        assert exchange.assets[AssetType.USDT].name == 'Tether USD'
        assert exchange.assets[AssetType.BTC].name == 'Bitcoin'

        # 检查交易对
        assert 'BTC/USDT' in exchange.trading_pairs
        btc_pair = exchange.trading_pairs['BTC/USDT']
        assert btc_pair.base_asset == AssetType.BTC
        assert btc_pair.quote_asset == AssetType.USDT
        assert btc_pair.current_price == 50000.0

        # 检查订单簿
        assert 'BTC/USDT' in exchange.order_books
        assert OrderType.BUY in exchange.order_books['BTC/USDT']
        assert OrderType.SELL in exchange.order_books['BTC/USDT']

    def test_place_buy_order(self, exchange: Exchange) -> None:
        """测试下买单"""
        order = exchange.place_order(
            user_id='user1',
            order_type=OrderType.BUY,
            asset=AssetType.BTC,
            quantity=1.0,
            price=50000.0,
        )

        assert order.user_id == 'user1'
        assert order.order_type == OrderType.BUY
        assert order.asset == AssetType.BTC
        assert order.quantity == 1.0
        assert order.price == 50000.0
        assert order.status == 'pending'

        # 检查订单是否在订单簿中
        assert order in exchange.order_books['BTC/USDT'][OrderType.BUY]
        assert order.id in exchange.orders

    def test_place_sell_order(self, exchange: Exchange) -> None:
        """测试下卖单"""
        order = exchange.place_order(
            user_id='user2',
            order_type=OrderType.SELL,
            asset=AssetType.BTC,
            quantity=0.5,
            price=50000.0,
        )

        assert order.user_id == 'user2'
        assert order.order_type == OrderType.SELL
        assert order.asset == AssetType.BTC
        assert order.quantity == 0.5
        assert order.price == 50000.0
        assert order.status == 'pending'

        # 检查订单是否在订单簿中
        assert order in exchange.order_books['BTC/USDT'][OrderType.SELL]
        assert order.id in exchange.orders

    def test_order_matching_same_price(self, exchange: Exchange) -> None:
        """测试相同价格的订单匹配"""
        # 下买单
        buy_order = exchange.place_order(
            user_id='user1',
            order_type=OrderType.BUY,
            asset=AssetType.BTC,
            quantity=1.0,
            price=50000.0,
        )

        # 下卖单
        sell_order = exchange.place_order(
            user_id='user2',
            order_type=OrderType.SELL,
            asset=AssetType.BTC,
            quantity=0.5,
            price=50000.0,
        )

        # 检查成交记录
        trades = exchange.get_recent_trades(AssetType.BTC)
        assert len(trades) == 1

        trade = trades[0]
        assert trade.buy_order_id == buy_order.id
        assert trade.sell_order_id == sell_order.id
        assert trade.quantity == 0.5
        assert trade.price == 50000.0

        # 检查订单状态
        buy_order = exchange.get_order(buy_order.id)
        sell_order = exchange.get_order(sell_order.id)

        assert buy_order.filled_quantity == 0.5
        assert buy_order.remaining_quantity == 0.5
        assert buy_order.status == 'partially_filled'

        assert sell_order.filled_quantity == 0.5
        assert sell_order.remaining_quantity == 0.0
        assert sell_order.status == 'filled'

    def test_order_matching_different_prices(self, exchange: Exchange) -> None:
        """测试不同价格的订单匹配"""
        # 下高价买单
        exchange.place_order(
            user_id='user1',
            order_type=OrderType.BUY,
            asset=AssetType.BTC,
            quantity=1.0,
            price=50100.0,
        )

        # 下低价卖单
        exchange.place_order(
            user_id='user2',
            order_type=OrderType.SELL,
            asset=AssetType.BTC,
            quantity=0.5,
            price=50000.0,
        )

        # 检查成交记录
        trades = exchange.get_recent_trades(AssetType.BTC)
        assert len(trades) == 1

        trade = trades[0]
        assert trade.quantity == 0.5
        assert trade.price == 50000.0  # 按卖单价格成交

        # 检查价格更新
        btc_pair = exchange.get_trading_pair(AssetType.BTC)
        assert btc_pair.current_price == 50000.0

    def test_order_book_ordering(self, exchange: Exchange) -> None:
        """测试订单簿排序"""
        # 下多个买单，价格不同
        exchange.place_order(
            user_id='user1',
            order_type=OrderType.BUY,
            asset=AssetType.BTC,
            quantity=1.0,
            price=50000.0,
        )

        exchange.place_order(
            user_id='user2',
            order_type=OrderType.BUY,
            asset=AssetType.BTC,
            quantity=1.0,
            price=50100.0,
        )

        exchange.place_order(
            user_id='user3',
            order_type=OrderType.BUY,
            asset=AssetType.BTC,
            quantity=1.0,
            price=49900.0,
        )

        # 检查买单排序（价格降序）
        buy_orders = exchange.order_books['BTC/USDT'][OrderType.BUY]
        assert buy_orders[0].price == 50100.0  # 最高价在前
        assert buy_orders[1].price == 50000.0
        assert buy_orders[2].price == 49900.0  # 最低价在后

        # 下多个卖单，价格不同
        exchange.place_order(
            user_id='user4',
            order_type=OrderType.SELL,
            asset=AssetType.BTC,
            quantity=1.0,
            price=50200.0,
        )

        exchange.place_order(
            user_id='user5',
            order_type=OrderType.SELL,
            asset=AssetType.BTC,
            quantity=1.0,
            price=50150.0,
        )

        exchange.place_order(
            user_id='user6',
            order_type=OrderType.SELL,
            asset=AssetType.BTC,
            quantity=1.0,
            price=50300.0,
        )

        # 检查卖单排序（价格升序）
        sell_orders = exchange.order_books['BTC/USDT'][OrderType.SELL]
        assert sell_orders[0].price == 50150.0  # 最低价在前
        assert sell_orders[1].price == 50200.0
        assert sell_orders[2].price == 50300.0  # 最高价在后

    def test_cancel_order(self, exchange: Exchange) -> None:
        """测试取消订单"""
        # 下订单
        order = exchange.place_order(
            user_id='user1',
            order_type=OrderType.BUY,
            asset=AssetType.BTC,
            quantity=1.0,
            price=50000.0,
        )

        # 取消订单
        result = exchange.cancel_order(order.id)
        assert result is True

        # 检查订单状态
        cancelled_order = exchange.get_order(order.id)
        assert cancelled_order.status == 'cancelled'

        # 检查订单是否从订单簿中移除
        assert order not in exchange.order_books['BTC/USDT'][OrderType.BUY]

    def test_cancel_filled_order(self, exchange: Exchange) -> None:
        """测试取消已成交订单"""
        # 下买单和卖单使其成交
        exchange.place_order(
            user_id='user1',
            order_type=OrderType.BUY,
            asset=AssetType.BTC,
            quantity=1.0,
            price=50000.0,
        )

        sell_order = exchange.place_order(
            user_id='user2',
            order_type=OrderType.SELL,
            asset=AssetType.BTC,
            quantity=1.0,
            price=50000.0,
        )

        # 尝试取消已成交的卖单
        result = exchange.cancel_order(sell_order.id)
        assert result is False

    def test_get_order_book(self, exchange: Exchange) -> None:
        """测试获取订单簿"""
        # 下一些订单
        exchange.place_order(
            user_id='user1',
            order_type=OrderType.BUY,
            asset=AssetType.BTC,
            quantity=1.0,
            price=50000.0,
        )

        exchange.place_order(
            user_id='user2',
            order_type=OrderType.SELL,
            asset=AssetType.BTC,
            quantity=0.5,
            price=50100.0,
        )

        # 获取订单簿
        order_book = exchange.get_order_book(AssetType.BTC)

        assert OrderType.BUY in order_book
        assert OrderType.SELL in order_book
        assert len(order_book[OrderType.BUY]) == 1
        assert len(order_book[OrderType.SELL]) == 1

    def test_get_trading_pair(self, exchange: Exchange) -> None:
        """测试获取交易对信息"""
        pair = exchange.get_trading_pair(AssetType.BTC)

        assert pair is not None
        assert pair.base_asset == AssetType.BTC
        assert pair.quote_asset == AssetType.USDT
        assert pair.current_price == 50000.0
        assert pair.symbol == 'BTC/USDT'

    def test_get_recent_trades(self, exchange: Exchange) -> None:
        """测试获取最近成交记录"""
        # 下订单产生成交
        exchange.place_order(
            user_id='user1',
            order_type=OrderType.BUY,
            asset=AssetType.BTC,
            quantity=1.0,
            price=50000.0,
        )

        exchange.place_order(
            user_id='user2',
            order_type=OrderType.SELL,
            asset=AssetType.BTC,
            quantity=0.5,
            price=50000.0,
        )

        # 获取成交记录
        trades = exchange.get_recent_trades(AssetType.BTC)
        assert len(trades) == 1

        trades = exchange.get_recent_trades(AssetType.BTC, limit=5)
        assert len(trades) <= 5
