"""撮合引擎。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tmo.core.order import Order, Side, Trade


if TYPE_CHECKING:
    from tmo.core.order_book import OrderBook


class Matcher:
    """价格优先、时间优先撮合引擎。"""

    def match(self, order: Order, book: OrderBook) -> tuple[list[Trade], float]:
        """对订单在指定订单簿上执行撮合，返回 (成交列表, 剩余未成交数量)。"""
        if order.side is Side.BUY:
            return self._match_buy(order, book)
        return self._match_sell(order, book)

    def _match_buy(self, order: Order, book: OrderBook) -> tuple[list[Trade], float]:
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
                    # STP: cancel the resting order
                    book._orders.pop(resting.order_id, None)
                    continue
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

    def _match_sell(self, order: Order, book: OrderBook) -> tuple[list[Trade], float]:
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
                    # STP: cancel the resting order
                    book._orders.pop(resting.order_id, None)
                    continue
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
