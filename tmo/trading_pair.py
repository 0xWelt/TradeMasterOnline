"""交易对核心逻辑。

该模块实现了交易对引擎，负责管理订单簿、执行交易撮合、处理订单生命周期，
以及维护价格发现和交易历史记录。
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from .constants import EPSILON, OrderStatus, OrderType, TradingPairType
from .typing import Order, TradeSettlement


if TYPE_CHECKING:
    from .user import User


class OrderBookLevel(BaseModel):
    """订单簿层级信息。

    表示订单簿中特定价格层级的信息，包含价格和对应的总数量。

    Attributes:
        price: 订单价格。
        quantity: 该价格层级的总数量。
    """

    price: float = Field(gt=0, description='订单价格')
    quantity: float = Field(gt=0, description='该价格层级的总数量')


class OrderBookSnapshot(BaseModel):
    """订单簿快照。

    表示特定时间点订单簿的完整状态，包含买单和卖单信息。

    Attributes:
        bids: 买单列表，按价格降序排列。
        asks: 卖单列表，按价格升序排列。
    """

    bids: list[OrderBookLevel] = Field(default_factory=list, description='买单列表')
    asks: list[OrderBookLevel] = Field(default_factory=list, description='卖单列表')


class TradingPairEngine:
    """交易对引擎，管理订单簿和交易撮合。

    该类负责特定交易对的所有交易相关操作，包括订单管理、撮合执行、
    价格更新和用户余额处理。采用价格-时间优先的撮合算法。

    Attributes:
        base_asset: 基础资产类型（如BTC）。
        quote_asset: 计价资产类型（如USDT）。
        current_price: 当前市场价格，基于最新成交价。
        last_update: 价格最后更新时间。
        orders: 订单字典，按订单类型分类存储所有订单。
        trade_history: 交易历史记录，最多保留1000条。
    """

    def __init__(self, trading_pair_type: TradingPairType, users: dict[str, User]):
        """初始化交易对引擎。

        Args:
            trading_pair_type: 交易对类型，定义基础资产和计价资产。
            users: 用户字典，用于通过user_id查找用户对象。
        """
        self.trading_pair_type = trading_pair_type
        self.base_asset = trading_pair_type.base_asset
        self.quote_asset = trading_pair_type.quote_asset
        self.current_price = trading_pair_type.initial_price
        self.last_update = datetime.now()
        self.users = users

        # 订单簿 - 使用字典统一管理
        self.orders: dict[OrderType, list[Order]] = {
            OrderType.BUY: [],
            OrderType.SELL: [],
            OrderType.MARKET_BUY: [],
            OrderType.MARKET_SELL: [],
        }
        self.trade_history: list[TradeSettlement] = []

    # ====================
    # 公共API方法
    # ====================

    def place_order(
        self,
        user: User,
        order_type: OrderType,
        base_amount: float | None = None,
        price: float | None = None,
        quote_amount: float | None = None,
    ) -> Order:
        """下单并立即执行匹配。

        处理完整的订单生命周期：参数验证、余额检查、订单插入和自动撮合。
        支持价格交叉和自成交。

        Args:
            user: 下单用户。
            order_type: 订单类型（BUY/SELL/MARKET_BUY/MARKET_SELL）。
            base_amount: 基础资产数量，与quote_amount二选一。
            price: 订单价格，限价订单必填。
            quote_amount: 计价资产金额，与base_amount二选一。

        Returns:
            Order: 创建的订单对象，已执行撮合。

        Raises:
            ValueError: 参数不合法或余额不足。
        """
        self._validate_user_balance(user, order_type, base_amount, price, quote_amount)

        order = Order(
            user_id=user.id,
            order_type=order_type,
            trading_pair=self.trading_pair_type,
            base_amount=base_amount,
            price=price,
            quote_amount=quote_amount,
        )

        self._insert_order(order)
        user.add_active_order(order)
        self._match_orders()
        return order

    def cancel_order(self, order: Order, user: User) -> bool:
        """取消订单。

        从订单簿中移除订单并更新订单状态。

        Args:
            order: 要取消的订单。

        Returns:
            bool: 取消成功返回True，失败返回False。
        """
        assert not order.is_filled
        order.status = OrderStatus.CANCELLED
        self.orders[order.order_type].remove(order)
        user.move_order_to_completed(order)

    def get_order_book(self) -> OrderBookSnapshot:
        """获取订单簿快照。

        Returns:
            OrderBookSnapshot: 订单簿快照，包含买单和卖单信息。
        """
        bids = [
            OrderBookLevel(price=order.price, quantity=order.remaining_base_amount)
            for order in self.orders[OrderType.BUY]
            if order.remaining_base_amount > EPSILON
        ]
        asks = [
            OrderBookLevel(price=order.price, quantity=order.remaining_base_amount)
            for order in self.orders[OrderType.SELL]
            if order.remaining_base_amount > EPSILON
        ]
        return OrderBookSnapshot(bids=bids, asks=asks)

    def get_recent_trades(self, limit: int = 10) -> list[TradeSettlement]:
        """获取最近的交易记录。

        Args:
            limit: 返回的最大交易数量。

        Returns:
            list: 最近的交易记录列表，按时间倒序排列。
        """
        return self.trade_history[-limit:] if self.trade_history else []

    def get_current_price(self) -> float:
        """获取交易对当前市场价格。

        Returns:
            float: 基于最新成交价的当前市场价格。
        """
        return self.current_price

    # ====================
    # 订单管理内部方法
    # ====================

    def _validate_user_balance(
        self,
        user: User,
        order_type: OrderType,
        base_amount: float | None,
        price: float | None,
        quote_amount: float | None,
    ) -> None:
        """验证用户余额是否充足。

        Args:
            user: 用户对象
            order_type: 订单类型
            base_amount: 基础资产数量
            price: 订单价格
            quote_amount: 计价资产金额

        Raises:
            ValueError: 余额不足
        """
        if order_type in [OrderType.BUY, OrderType.MARKET_BUY]:
            # 买单需要计价资产
            if order_type == OrderType.MARKET_BUY:
                if quote_amount is not None:
                    required_quote = quote_amount
                elif base_amount is not None:
                    required_quote = base_amount * self.current_price
                else:
                    required_quote = 0
            else:  # 限价买单
                if base_amount is not None and price is not None:
                    required_quote = base_amount * price
                elif quote_amount is not None:
                    required_quote = quote_amount
                else:
                    required_quote = 0

            available_quote = user.get_available_balance(self.quote_asset)
            if required_quote > available_quote:
                raise ValueError(
                    f'{self.quote_asset.value}余额不足，需要 {required_quote:.2f}，可用 {available_quote:.2f}'
                )

        else:  # 卖单
            # 卖单需要基础资产
            if order_type == OrderType.MARKET_SELL:
                if base_amount is not None:
                    required_base = base_amount
                elif quote_amount is not None:
                    required_base = quote_amount / self.current_price
                else:
                    required_base = 0
            else:  # 限价卖单
                if base_amount is not None:
                    required_base = base_amount
                elif quote_amount is not None and price is not None:
                    required_base = quote_amount / price
                else:
                    required_base = 0

            available_base = user.get_available_balance(self.base_asset)
            if required_base > available_base:
                raise ValueError(
                    f'{self.base_asset.value}余额不足，需要 {required_base:.8f}，可用 {available_base:.8f}'
                )

    def _insert_order(self, order: Order) -> None:
        """将订单插入到相应的订单簿中。

        根据订单类型将订单插入到对应的订单簿，并确保价格排序正确。

        Args:
            order: 要插入的订单。
        """
        if order.order_type == OrderType.BUY:
            self._insert_buy_order(order)
        elif order.order_type == OrderType.SELL:
            self._insert_sell_order(order)
        else:
            # 市价订单直接添加到对应列表
            self.orders[order.order_type].append(order)

    def _remove_order(self, order: Order) -> bool:
        """从订单簿中移除订单。

        Args:
            order: 要移除的订单。

        Returns:
            bool: 移除成功返回True，失败返回False。
        """
        orders = self.orders.get(order.order_type, [])
        if order in orders:
            orders.remove(order)
            return True
        return False

    def _insert_buy_order(self, order: Order) -> None:
        """插入买单到订单簿（价格降序）。

        Args:
            order: 买单对象。
        """
        orders = self.orders[OrderType.BUY]
        for i, existing_order in enumerate(orders):
            if order.price > existing_order.price:
                orders.insert(i, order)
                return
        orders.append(order)

    def _insert_sell_order(self, order: Order) -> None:
        """插入卖单到订单簿（价格升序）。

        Args:
            order: 卖单对象。
        """
        orders = self.orders[OrderType.SELL]
        for i, existing_order in enumerate(orders):
            if order.price < existing_order.price:
                orders.insert(i, order)
                return
        orders.append(order)

    # ====================
    # 交易撮合内部方法
    # ====================

    def _match_orders(self) -> None:
        """执行订单撮合。

        处理所有待成交订单，包括市价订单和限价订单的匹配。
        """
        trades = []

        # 先处理市价订单
        market_trades = self._execute_market_orders()
        trades.extend(market_trades)

        # 再处理限价订单匹配
        limit_trades = self._match_limit_orders()
        trades.extend(limit_trades)

        # 更新价格
        if trades:
            self._update_price_from_trades(trades)

    def _execute_market_orders(self) -> list[TradeSettlement]:
        """执行所有市价订单。

        Returns:
            list: 生成的交易记录列表。
        """
        trades = []

        # 处理市价买单
        for market_buy in self.orders[OrderType.MARKET_BUY][:]:
            trades.extend(self._execute_market_buy(market_buy))

        # 处理市价卖单
        for market_sell in self.orders[OrderType.MARKET_SELL][:]:
            trades.extend(self._execute_market_sell(market_sell))

        return trades

    def _execute_market_buy(self, market_buy: Order) -> list[TradeSettlement]:
        """执行单个市价买单。

        从卖单簿中按价格从低到高成交，立即成交所有可用卖单。

        Args:
            market_buy: 市价买单。

        Returns:
            list: 生成的交易记录列表。
        """
        trades = []

        # 从卖单簿中按价格从低到高成交所有可用卖单
        while self.orders[OrderType.SELL] and not market_buy.is_filled:
            sell_order = self.orders[OrderType.SELL][0]
            trade_price = sell_order.price
            trade_quantity = min(
                sell_order.remaining_base_amount, market_buy.remaining_quote_amount / trade_price
            )

            trade = self._create_trade(market_buy, sell_order, trade_quantity, trade_price)
            trades.append(trade)

            # 如果没有任何订单被清理，说明可能有精度问题，退出循环
            if not any(order.is_filled for order in [market_buy, sell_order]):
                raise ValueError('订单簿中存在未成交订单，可能存在精度问题')

        return trades

    def _execute_market_sell(self, market_sell: Order) -> list[TradeSettlement]:
        """执行单个市价卖单。

        从买单簿中按价格从高到低成交，立即成交所有可用买单。

        Args:
            market_sell: 市价卖单。

        Returns:
            list: 生成的交易记录列表。
        """
        trades = []

        # 从买单簿中按价格从高到低成交所有可用买单
        while self.orders[OrderType.BUY] and not market_sell.is_filled:
            buy_order = self.orders[OrderType.BUY][0]
            trade_price = buy_order.price
            trade_quantity = min(buy_order.remaining_base_amount, market_sell.remaining_base_amount)

            trade = self._create_trade(buy_order, market_sell, trade_quantity, trade_price)
            trades.append(trade)

            # 如果没有任何订单被清理，说明可能有精度问题，退出循环
            if not any(order.is_filled for order in [buy_order, market_sell]):
                raise ValueError('订单簿中存在未成交订单，可能存在精度问题')

        return trades

    def _match_limit_orders(self) -> list[TradeSettlement]:
        """匹配限价订单。

        采用价格-时间优先算法匹配买单和卖单。

        Returns:
            list: 生成的交易记录列表。
        """
        trades = []

        while (
            self.orders[OrderType.BUY]
            and self.orders[OrderType.SELL]
            and self.orders[OrderType.BUY][0].price >= self.orders[OrderType.SELL][0].price
        ):
            best_buy = self.orders[OrderType.BUY][0]
            best_sell = self.orders[OrderType.SELL][0]

            trade_quantity = min(best_buy.remaining_base_amount, best_sell.remaining_base_amount)

            # 按照更早的订单价格成交
            if best_buy.timestamp <= best_sell.timestamp:
                trade_price = best_buy.price
            else:
                trade_price = best_sell.price

            trade = self._create_trade(best_buy, best_sell, trade_quantity, trade_price)
            trades.append(trade)

            # 如果没有任何订单被清理，说明可能有精度问题，退出循环
            if not any(order.is_filled for order in [best_buy, best_sell]):
                raise ValueError('订单簿中存在未成交订单，可能存在精度问题')

        return trades

    # ====================
    # 交易创建和更新方法
    # ====================

    def _create_trade(
        self,
        buy_order: Order,
        sell_order: Order,
        quantity: float,
        price: float,
    ) -> TradeSettlement:
        """创建交易记录。

        根据买卖订单和成交信息创建交易记录，更新订单状态，
        并处理用户余额更新。

        Args:
            buy_order: 买单对象。
            sell_order: 卖单对象。
            quantity: 成交数量。
            price: 成交价格。

        Returns:
            TradeSettlement: 交易记录。
        """
        # 创建交易记录并更新用户持仓
        trade = TradeSettlement(
            buy_order=buy_order,
            sell_order=sell_order,
            trading_pair=self.trading_pair_type,
            base_amount=quantity,
            price=price,
        )

        # 添加到滚动历史记录
        self.trade_history.append(trade)
        if len(self.trade_history) > 1000:
            self.trade_history = self.trade_history[-1000:]

        # 更新订单状态
        self._update_order_status(buy_order, trade)
        self._update_order_status(sell_order, trade)

        # 更新买卖双方的持仓
        self._update_user_balances_from_trade(trade)

        return trade

    def _update_order_status(self, order: Order, trade: TradeSettlement) -> None:
        """更新订单状态并清理已完成的订单。

        更新指定订单的状态，当订单完全成交时将其从活跃订单移动到已完成订单，
        并清理订单簿中所有已完成的订单。

        Args:
            order: 要更新的订单。
            trade: 交易记录。
        """
        # 更新订单已成交数量和金额
        order.filled_base_amount += trade.base_amount
        order.filled_quote_amount += trade.base_amount * trade.price

        # 更新订单状态
        if order.is_filled:
            order.status = OrderStatus.FILLED
            self.orders[order.order_type].remove(order)
            user = self.users[order.user_id]
            user.move_order_to_completed(order)
        elif order.is_partially_filled:
            order.status = OrderStatus.PARTIALLY_FILLED

    def _update_price_from_trades(self, trades: list[TradeSettlement]) -> None:
        """根据交易更新价格。

        Args:
            trades: 交易列表。
        """
        if trades:
            # 使用最后一笔交易的价格
            self.current_price = trades[-1].price
            self.last_update = datetime.now()

    def _update_user_balances_from_trade(self, trade: TradeSettlement) -> None:
        """根据交易记录更新用户总资产。

        交易结算时只更新用户的总资产，可用余额和锁定余额通过动态计算获得。

        Args:
            trade: 交易结算信息。
        """
        buyer = self.users[trade.buy_order.user_id]
        seller = self.users[trade.sell_order.user_id]
        trade_value = trade.base_amount * trade.price

        # 买家操作：获得基础资产，扣除计价资产
        buyer.update_total_asset(trade.trading_pair.base_asset, trade.base_amount)
        buyer.update_total_asset(trade.trading_pair.quote_asset, -trade_value)

        # 卖家操作：获得计价资产，扣除基础资产
        seller.update_total_asset(trade.trading_pair.quote_asset, trade_value)
        seller.update_total_asset(trade.trading_pair.base_asset, -trade.base_amount)
