"""限价订单簿。"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from tmo.core.matcher import Matcher
from tmo.core.order import Order, Side, Trade


if TYPE_CHECKING:
    from tmo.utils.types import AgentId, OrderId, PairId


class PriceLevel:
    """同一价格的订单队列（FIFO）。"""

    def __init__(self, price: float) -> None:
        """初始化价格档。

        Args:
            price: 价格档的价格。
        """
        self.price = price
        self.orders: deque[Order] = deque()  # 订单双端队列，按时间顺序排列
        self.total_qty = 0.0  # 该价格档的总数量

    def append(self, order: Order) -> None:
        """在队列尾部追加订单。

        Args:
            order: 待追加的订单。
        """
        self.orders.append(order)
        self.total_qty += order.quantity

    def remove(self, order_id: str) -> Order | None:
        """按 order_id 移除订单。

        Args:
            order_id: 要移除的订单标识。

        Returns:
            被移除的订单，如果不存在则返回 None。
        """
        for i, o in enumerate(self.orders):
            if o.order_id == order_id:
                self.orders.rotate(-i)
                removed = self.orders.popleft()
                self.orders.rotate(i)
                self.total_qty -= removed.quantity
                return removed
        return None

    def appendleft(self, order: Order) -> None:
        """在队列头部插入订单。

        Args:
            order: 待插入的订单。
        """
        self.orders.appendleft(order)
        self.total_qty += order.quantity

    def popleft(self) -> Order:
        """从队列头部取出订单。

        Returns:
            队列头部的订单。
        """
        order = self.orders.popleft()
        self.total_qty -= order.quantity
        return order

    def __bool__(self) -> bool:
        """判断队列是否非空。

        Returns:
            True 当且仅当队列中有订单。
        """
        return bool(self.orders)


class OrderBook:
    """单个交易对的限价订单簿。

    维护 bids（买单）和 asks（卖单）两个价格档字典，
    以及一个按 order_id 索引的活跃订单字典。
    """

    def __init__(self, pair_id: PairId) -> None:
        """初始化订单簿。

        Args:
            pair_id: 交易对标识。
        """
        self.pair_id = pair_id
        self._bids: dict[float, PriceLevel] = {}  # 买单队列（价格 -> 价格档）
        self._asks: dict[float, PriceLevel] = {}  # 卖单队列（价格 -> 价格档）
        self._orders: dict[str, Order] = {}  # 按 order_id 索引的所有活跃订单
        self._matcher = Matcher()  # 撮合引擎实例

    @property
    def bids(self) -> dict[float, PriceLevel]:
        """买单队列（价格降序遍历）。

        Returns:
            价格到价格档的字典。
        """
        return self._bids

    @property
    def asks(self) -> dict[float, PriceLevel]:
        """卖单队列（价格升序遍历）。

        Returns:
            价格到价格档的字典。
        """
        return self._asks

    @property
    def orders(self) -> dict[str, Order]:
        """所有活跃订单的只读副本。

        Returns:
            按 order_id 索引的订单字典副本。
        """
        return self._orders.copy()

    def place_order(self, order: Order, stp_mode: str = 'expire_maker') -> list[Trade]:
        """挂单并撮合，返回成交列表。

        先调用 Matcher 进行撮合，若有剩余未成交数量则作为 resting order 挂单。

        Args:
            order: 待挂单的订单。
            stp_mode: 自成交保护策略，默认 'expire_maker'。

        Returns:
            成交记录列表。
        """
        self._orders[order.order_id] = order
        trades, remaining = self._matcher.match(order, self, stp_mode)
        if remaining > 0:
            resting = Order(
                order_id=order.order_id,
                agent_id=order.agent_id,
                pair_id=order.pair_id,
                side=order.side,
                price=order.price,
                quantity=remaining,
                stp_mode=order.stp_mode,
            )
            self._add_resting(resting)
        else:
            self._orders.pop(order.order_id, None)
        return trades

    def cancel_order(self, order_id: OrderId) -> Order | None:
        """撤单，返回被撤的订单或 None。

        Args:
            order_id: 要取消的订单标识。

        Returns:
            被撤的订单，如果不存在则返回 None。
        """
        order = self._orders.pop(order_id, None)
        if order is None:
            return None
        book = self._bids if order.is_buy() else self._asks
        level = book.get(order.price)
        if level is not None:
            level.remove(order_id)
            if not level:
                del book[order.price]
        return order

    def get_agent_outstanding(self, agent_id: AgentId, side: Side) -> float:
        """返回 agent 在该订单簿指定方向上的未成交挂单总量。

        Args:
            agent_id: 智能体标识。
            side: 交易方向。

        Returns:
            未成交挂单总数量。
        """
        book = self._bids if side is Side.BUY else self._asks
        total = 0.0
        for level in book.values():
            for order in level.orders:
                if order.agent_id == agent_id:
                    total += order.quantity
        return total

    def get_snapshot(self, n_levels: int = 5) -> dict[str, list[tuple[float, float]]]:
        """返回前 n 档的 (价格, 总量) 快照。

        Args:
            n_levels: 要返回的价格档数量，默认 5。

        Returns:
            包含 'bids' 和 'asks' 两个字典，每个值为 [(价格, 总量), ...] 列表。
        """
        bid_prices = sorted(self._bids.keys(), reverse=True)[:n_levels]
        ask_prices = sorted(self._asks.keys())[:n_levels]
        return {
            'bids': [(p, self._bids[p].total_qty) for p in bid_prices],
            'asks': [(p, self._asks[p].total_qty) for p in ask_prices],
        }

    def _add_resting(self, order: Order) -> None:
        """将 resting order 加入订单簿内部数据结构。

        Args:
            order: 待加入的 resting order。
        """
        book = self._bids if order.is_buy() else self._asks
        if order.price not in book:
            book[order.price] = PriceLevel(order.price)
        book[order.price].append(order)
        self._orders[order.order_id] = order
