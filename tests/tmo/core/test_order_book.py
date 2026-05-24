"""测试 OrderBook 和 PriceLevel。"""

from __future__ import annotations

from tmo.core.order import Order, Side
from tmo.core.order_book import OrderBook, PriceLevel


class TestPriceLevel:
    """PriceLevel 测试。"""

    def test_append_and_total_qty(self) -> None:
        """测试追加订单后 total_qty 正确累加。"""
        level = PriceLevel(price=100.0)
        level.append(
            Order(
                order_id='o1', agent_id='a1', pair_id='P', side=Side.BUY, price=100.0, quantity=1.0
            )
        )
        level.append(
            Order(
                order_id='o2', agent_id='a2', pair_id='P', side=Side.BUY, price=100.0, quantity=2.0
            )
        )
        assert level.total_qty == 3.0

    def test_remove_existing(self) -> None:
        """测试移除已存在的订单。"""
        level = PriceLevel(price=100.0)
        order = Order(
            order_id='o1', agent_id='a1', pair_id='P', side=Side.BUY, price=100.0, quantity=1.0
        )
        level.append(order)
        removed = level.remove('o1')
        assert removed is not None
        assert removed.order_id == 'o1'
        assert level.total_qty == 0.0
        assert not level

    def test_remove_missing(self) -> None:
        """测试移除不存在的订单返回 None。"""
        level = PriceLevel(price=100.0)
        assert level.remove('o1') is None

    def test_popleft(self) -> None:
        """测试从队列头部取出订单。"""
        level = PriceLevel(price=100.0)
        order = Order(
            order_id='o1', agent_id='a1', pair_id='P', side=Side.BUY, price=100.0, quantity=1.0
        )
        level.append(order)
        popped = level.popleft()
        assert popped.order_id == 'o1'
        assert level.total_qty == 0.0


class TestOrderBook:
    """OrderBook 测试。"""

    def test_place_buy_order_resting(self) -> None:
        """测试 BUY 订单挂单后成为 resting order。"""
        book = OrderBook('P')
        order = Order(
            order_id='o1', agent_id='a1', pair_id='P', side=Side.BUY, price=100.0, quantity=1.0
        )
        trades = book.place_order(order)
        assert trades == []
        assert 'o1' in book.orders
        assert 100.0 in book.bids

    def test_place_sell_order_resting(self) -> None:
        """测试 SELL 订单挂单后成为 resting order。"""
        book = OrderBook('P')
        order = Order(
            order_id='o1', agent_id='a1', pair_id='P', side=Side.SELL, price=101.0, quantity=1.0
        )
        trades = book.place_order(order)
        assert trades == []
        assert 101.0 in book.asks

    def test_match_buy_against_ask(self) -> None:
        """测试 BUY 订单与 ask 撮合成交。"""
        book = OrderBook('P')
        sell = Order(
            order_id='o1', agent_id='a1', pair_id='P', side=Side.SELL, price=100.0, quantity=1.0
        )
        book.place_order(sell)
        buy = Order(
            order_id='o2', agent_id='a2', pair_id='P', side=Side.BUY, price=100.0, quantity=1.0
        )
        trades = book.place_order(buy)
        assert len(trades) == 1
        assert trades[0].price == 100.0
        assert trades[0].quantity == 1.0
        assert 'o1' not in book.orders
        assert 'o2' not in book.orders

    def test_cancel_order(self) -> None:
        """测试取消订单。"""
        book = OrderBook('P')
        order = Order(
            order_id='o1', agent_id='a1', pair_id='P', side=Side.BUY, price=100.0, quantity=1.0
        )
        book.place_order(order)
        removed = book.cancel_order('o1')
        assert removed is not None
        assert 'o1' not in book.orders
        assert 100.0 not in book.bids

    def test_cancel_missing(self) -> None:
        """测试取消不存在的订单返回 None。"""
        book = OrderBook('P')
        assert book.cancel_order('o1') is None

    def test_get_snapshot(self) -> None:
        """测试订单簿快照功能。"""
        book = OrderBook('P')
        book.place_order(
            Order(
                order_id='o1', agent_id='a1', pair_id='P', side=Side.BUY, price=100.0, quantity=1.0
            )
        )
        book.place_order(
            Order(
                order_id='o2', agent_id='a2', pair_id='P', side=Side.BUY, price=99.0, quantity=2.0
            )
        )
        book.place_order(
            Order(
                order_id='o3', agent_id='a3', pair_id='P', side=Side.SELL, price=101.0, quantity=3.0
            )
        )
        snap = book.get_snapshot(n_levels=2)
        assert len(snap['bids']) == 2
        assert snap['bids'][0] == (100.0, 1.0)
        assert snap['bids'][1] == (99.0, 2.0)
        assert len(snap['asks']) == 1
        assert snap['asks'][0] == (101.0, 3.0)
