"""测试 Matcher 撮合逻辑。"""

from __future__ import annotations

from tmo.core.order import Order, Side
from tmo.core.order_book import OrderBook


class TestMatcher:
    """Matcher 撮合逻辑测试。"""

    def test_buy_matches_best_ask(self) -> None:
        """测试 BUY 订单匹配最低 ask 价格成交。"""
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
        """测试 BUY 价格低于 ask 时不成交，成为 resting order。"""
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
        """测试 SELL 订单匹配最高 bid 价格成交。"""
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
        """测试部分填充：BUY 数量大于 SELL 时，剩余成为 resting order。"""
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
        """测试跨多个价格档的撮合。"""
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
        """测试默认 STP (expire_maker)：自成交时取消 resting order。"""
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
        """测试 STP 取消后跳到下一个价格档撮合。"""
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

    def test_stp_expire_taker(self) -> None:
        """测试 expire_taker 策略：取消 incoming order。"""
        book = OrderBook('P')
        book.place_order(
            Order(
                order_id='s1', agent_id='a1', pair_id='P', side=Side.SELL, price=100.0, quantity=1.0
            )
        )
        trades = book.place_order(
            Order(
                order_id='b1',
                agent_id='a1',
                pair_id='P',
                side=Side.BUY,
                price=100.0,
                quantity=1.0,
                stp_mode='expire_taker',
            ),
            stp_mode='expire_taker',
        )
        # incoming order cancelled, resting order preserved
        assert trades == []
        assert 's1' in book.orders
        assert 'b1' not in book.orders

    def test_stp_expire_both(self) -> None:
        """测试 expire_both 策略：两边同时取消。"""
        book = OrderBook('P')
        book.place_order(
            Order(
                order_id='s1', agent_id='a1', pair_id='P', side=Side.SELL, price=100.0, quantity=1.0
            )
        )
        trades = book.place_order(
            Order(
                order_id='b1',
                agent_id='a1',
                pair_id='P',
                side=Side.BUY,
                price=100.0,
                quantity=1.0,
                stp_mode='expire_both',
            ),
            stp_mode='expire_both',
        )
        # both orders cancelled
        assert trades == []
        assert 's1' not in book.orders
        assert 'b1' not in book.orders

    def test_stp_none_skips_to_next_level(self) -> None:
        """测试 none 策略：跳过自订单，尝试其他价格档。"""
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
                order_id='b1',
                agent_id='a1',
                pair_id='P',
                side=Side.BUY,
                price=101.0,
                quantity=2.0,
                stp_mode='none',
            ),
            stp_mode='none',
        )
        # s1 skipped (not cancelled), b1 matches s2
        assert len(trades) == 1
        assert trades[0].price == 101.0
        assert trades[0].seller_id == 'a2'
        assert 's1' in book.orders
