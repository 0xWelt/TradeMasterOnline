"""测试 Matcher 撮合逻辑。"""

from __future__ import annotations

from tmo.core.order import Order, Side
from tmo.core.order_book import OrderBook


class TestMatcher:
    def test_buy_matches_best_ask(self) -> None:
        book = OrderBook('P')
        book.place_order(
            Order(
                order_id='s1', agent_id='a1', pair_id='P', side=Side.SELL, price=100.0, quantity=1.0
            )
        )
        trades = book.place_order(
            Order(
                order_id='b1', agent_id='a2', pair_id='P', side=Side.BUY, price=100.0, quantity=1.0
            )
        )
        assert len(trades) == 1
        assert trades[0].price == 100.0
        assert trades[0].quantity == 1.0
        assert trades[0].buyer_id == 'a2'
        assert trades[0].seller_id == 'a1'

    def test_buy_no_match_price_too_low(self) -> None:
        book = OrderBook('P')
        book.place_order(
            Order(
                order_id='s1', agent_id='a1', pair_id='P', side=Side.SELL, price=101.0, quantity=1.0
            )
        )
        trades = book.place_order(
            Order(
                order_id='b1', agent_id='a2', pair_id='P', side=Side.BUY, price=100.0, quantity=1.0
            )
        )
        assert trades == []
        assert 'b1' in book.orders

    def test_sell_matches_best_bid(self) -> None:
        book = OrderBook('P')
        book.place_order(
            Order(
                order_id='b1', agent_id='a1', pair_id='P', side=Side.BUY, price=100.0, quantity=1.0
            )
        )
        trades = book.place_order(
            Order(
                order_id='s1', agent_id='a2', pair_id='P', side=Side.SELL, price=100.0, quantity=1.0
            )
        )
        assert len(trades) == 1
        assert trades[0].price == 100.0
        assert trades[0].seller_id == 'a2'

    def test_partial_fill(self) -> None:
        book = OrderBook('P')
        book.place_order(
            Order(
                order_id='s1', agent_id='a1', pair_id='P', side=Side.SELL, price=100.0, quantity=1.0
            )
        )
        trades = book.place_order(
            Order(
                order_id='b1', agent_id='a2', pair_id='P', side=Side.BUY, price=100.0, quantity=2.0
            )
        )
        assert len(trades) == 1
        assert trades[0].quantity == 1.0
        assert 's1' not in book.orders
        assert 'b1' in book.orders
        assert book.orders['b1'].quantity == 1.0

    def test_multiple_levels(self) -> None:
        book = OrderBook('P')
        book.place_order(
            Order(
                order_id='s1', agent_id='a1', pair_id='P', side=Side.SELL, price=100.0, quantity=1.0
            )
        )
        book.place_order(
            Order(
                order_id='s2', agent_id='a1', pair_id='P', side=Side.SELL, price=101.0, quantity=1.0
            )
        )
        trades = book.place_order(
            Order(
                order_id='b1', agent_id='a2', pair_id='P', side=Side.BUY, price=101.0, quantity=2.0
            )
        )
        assert len(trades) == 2
        assert trades[0].price == 100.0
        assert trades[1].price == 101.0

    def test_self_trade_prevention(self) -> None:
        book = OrderBook('P')
        book.place_order(
            Order(
                order_id='s1', agent_id='a1', pair_id='P', side=Side.SELL, price=100.0, quantity=1.0
            )
        )
        trades = book.place_order(
            Order(
                order_id='b1', agent_id='a1', pair_id='P', side=Side.BUY, price=100.0, quantity=1.0
            )
        )
        # STP cancels the resting order (s1), b1 has no counterparty -> rests
        assert trades == []
        assert 's1' not in book.orders
        assert 'b1' in book.orders

    def test_self_trade_skips_to_next_level(self) -> None:
        book = OrderBook('P')
        book.place_order(
            Order(
                order_id='s1', agent_id='a1', pair_id='P', side=Side.SELL, price=100.0, quantity=1.0
            )
        )
        book.place_order(
            Order(
                order_id='s2', agent_id='a2', pair_id='P', side=Side.SELL, price=101.0, quantity=1.0
            )
        )
        trades = book.place_order(
            Order(
                order_id='b1', agent_id='a1', pair_id='P', side=Side.BUY, price=101.0, quantity=2.0
            )
        )
        # s1 cancelled by STP, b1 matches s2
        assert len(trades) == 1
        assert trades[0].price == 101.0
        assert trades[0].seller_id == 'a2'
        assert 's1' not in book.orders
