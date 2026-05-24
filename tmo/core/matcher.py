"""撮合引擎。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tmo.core.order import Order, OrderStatus, Side, Trade


if TYPE_CHECKING:
    from tmo.core.order_book import OrderBook


class Matcher:
    """价格优先、时间优先撮合引擎。

    支持可配置的自成交保护（STP）策略：
    - expire_maker: 取消 resting order（被动方），incoming 继续撮合。
    - expire_taker: 取消 incoming order（主动方），resting 保留。
    - expire_both: 两边同时取消。
    - none: 跳过该 resting order，尝试其他价格档。
    """

    def match(
        self, order: Order, book: OrderBook, stp_mode: str = 'expire_maker'
    ) -> tuple[list[Trade], float]:
        """对订单在指定订单簿上执行撮合。

        Args:
            order: 待撮合的 incoming order。
            book: 目标订单簿。
            stp_mode: 自成交保护策略，默认 'expire_maker'。

        Returns:
            (成交列表, 剩余未成交数量)。
        """
        if order.side is Side.BUY:
            return self._match_buy(order, book, stp_mode)
        return self._match_sell(order, book, stp_mode)

    def _match_buy(self, order: Order, book: OrderBook, stp_mode: str) -> tuple[list[Trade], float]:
        """BUY 订单撮合逻辑。

        从最低 ask 价格开始匹配，要求 ask price <= order price。
        同一价格档内按 FIFO 顺序匹配。

        Args:
            order: 待撮合的 BUY 订单。
            book: 目标订单簿。
            stp_mode: 自成交保护策略。

        Returns:
            (成交列表, 剩余未成交数量)。
        """
        trades: list[Trade] = []
        remaining = order.quantity
        skip_prices: set[float] = set()
        while remaining > 0 and book.asks:
            candidates = [p for p in book.asks if p <= order.price and p not in skip_prices]
            if not candidates:
                break
            best_ask = min(candidates)
            level = book.asks[best_ask]
            n_orders = len(level.orders)
            matched = False
            for _ in range(n_orders):
                if remaining <= 0 or not level:
                    break
                resting = level.popleft()
                if resting.agent_id == order.agent_id:
                    if stp_mode == 'expire_maker':
                        book._orders.pop(resting.order_id, None)
                        continue
                    if stp_mode == 'expire_taker':
                        level.append(resting)
                        remaining = 0.0
                        break
                    if stp_mode == 'expire_both':
                        book._orders.pop(resting.order_id, None)
                        remaining = 0.0
                        break
                    # stp_mode == 'none'
                    level.append(resting)
                    break
                matched = True
                qty = min(remaining, resting.quantity)
                trades.append(
                    Trade(
                        pair_id=book.pair_id,
                        price=resting.price,
                        quantity=qty,
                        buyer_id=order.agent_id,
                        seller_id=resting.agent_id,
                        buy_order_id=order.order_id,
                        sell_order_id=resting.order_id,
                    )
                )
                remaining -= qty
                if qty < resting.quantity:
                    updated = Order(
                        order_id=resting.order_id,
                        agent_id=resting.agent_id,
                        pair_id=resting.pair_id,
                        side=resting.side,
                        price=resting.price,
                        quantity=resting.quantity - qty,
                        stp_mode=resting.stp_mode,
                        status=OrderStatus.PARTIALLY_FILLED,
                        filled_qty=resting.filled_qty + qty,
                    )
                    level.appendleft(updated)
                    level.total_qty += updated.quantity
                else:
                    book._orders.pop(resting.order_id, None)
                break
            if not level:
                del book.asks[best_ask]
            if not matched:
                skip_prices.add(best_ask)
        return trades, remaining

    def _match_sell(
        self, order: Order, book: OrderBook, stp_mode: str
    ) -> tuple[list[Trade], float]:
        """SELL 订单撮合逻辑。

        从最高 bid 价格开始匹配，要求 bid price >= order price。
        同一价格档内按 FIFO 顺序匹配。

        Args:
            order: 待撮合的 SELL 订单。
            book: 目标订单簿。
            stp_mode: 自成交保护策略。

        Returns:
            (成交列表, 剩余未成交数量)。
        """
        trades: list[Trade] = []
        remaining = order.quantity
        skip_prices: set[float] = set()
        while remaining > 0 and book.bids:
            candidates = [p for p in book.bids if p >= order.price and p not in skip_prices]
            if not candidates:
                break
            best_bid = max(candidates)
            level = book.bids[best_bid]
            n_orders = len(level.orders)
            matched = False
            for _ in range(n_orders):
                if remaining <= 0 or not level:
                    break
                resting = level.popleft()
                if resting.agent_id == order.agent_id:
                    if stp_mode == 'expire_maker':
                        book._orders.pop(resting.order_id, None)
                        continue
                    if stp_mode == 'expire_taker':
                        level.append(resting)
                        remaining = 0.0
                        break
                    if stp_mode == 'expire_both':
                        book._orders.pop(resting.order_id, None)
                        remaining = 0.0
                        break
                    # stp_mode == 'none'
                    level.append(resting)
                    break
                matched = True
                qty = min(remaining, resting.quantity)
                trades.append(
                    Trade(
                        pair_id=book.pair_id,
                        price=resting.price,
                        quantity=qty,
                        buyer_id=resting.agent_id,
                        seller_id=order.agent_id,
                        buy_order_id=resting.order_id,
                        sell_order_id=order.order_id,
                    )
                )
                remaining -= qty
                if qty < resting.quantity:
                    updated = Order(
                        order_id=resting.order_id,
                        agent_id=resting.agent_id,
                        pair_id=resting.pair_id,
                        side=resting.side,
                        price=resting.price,
                        quantity=resting.quantity - qty,
                        stp_mode=resting.stp_mode,
                        status=OrderStatus.PARTIALLY_FILLED,
                        filled_qty=resting.filled_qty + qty,
                    )
                    level.appendleft(updated)
                    level.total_qty += updated.quantity
                else:
                    book._orders.pop(resting.order_id, None)
                break
            if not level:
                del book.bids[best_bid]
            if not matched:
                skip_prices.add(best_bid)
        return trades, remaining
