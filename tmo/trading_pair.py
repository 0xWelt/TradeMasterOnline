"""交易对核心逻辑。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from .constants import OrderStatus, OrderType, TradingPairType
from .typing import Order, TradeSettlement


if TYPE_CHECKING:
    from .typing import User


class TradingPairEngine:
    """交易对引擎，管理订单簿和交易撮合。"""

    def __init__(self, trading_pair_type: TradingPairType):
        self.base_asset = trading_pair_type.base_asset
        self.quote_asset = trading_pair_type.quote_asset
        self.current_price = trading_pair_type.initial_price
        self.last_update = datetime.now()

        self.buy_orders: list[Order] = []
        self.sell_orders: list[Order] = []
        self.market_buy_orders: list[Order] = []
        self.market_sell_orders: list[Order] = []
        self.trade_history: list[TradeSettlement] = []

    # ====================
    # 订单管理
    # ====================

    # ====================
    # 交易撮合
    # ====================

    def _create_trade(
        self,
        buy_order: Order,
        sell_order: Order,
        quantity: float,
        price: float,
    ) -> TradeSettlement | None:
        """创建交易记录。

        Args:
            buy_order: 买单。
            sell_order: 卖单。
            quantity: 成交数量。
            price: 成交价格。

        Returns:
            TradeSettlement: 交易记录，如果数量为0则返回None。
        """
        # 防止创建零大小的交易
        if quantity <= 1e-10:  # 设置最小交易阈值
            return None

        # 更新订单已成交数量和金额
        buy_order.filled_base_amount += quantity
        sell_order.filled_base_amount += quantity

        # 计算已成交的计价资产金额
        executed_quote = quantity * price
        buy_order.filled_quote_amount += executed_quote
        sell_order.filled_quote_amount += executed_quote

        # 计算实际平均成交价格
        if buy_order.filled_base_amount > 0:
            buy_order.average_execution_price = (
                buy_order.filled_quote_amount / buy_order.filled_base_amount
            )
        if sell_order.filled_base_amount > 0:
            sell_order.average_execution_price = (
                sell_order.filled_quote_amount / sell_order.filled_base_amount
            )

        # 更新订单状态
        self._update_order_status(buy_order)
        self._update_order_status(sell_order)

        # 创建交易记录并更新用户持仓
        trade = TradeSettlement(
            buy_order=buy_order,
            sell_order=sell_order,
            trading_pair=TradingPairType(f'{self.base_asset.value}/{self.quote_asset.value}'),
            base_amount=quantity,
            price=price,
        )

        # 更新买卖双方的持仓（从Order回调移动到TradeSettlement）
        self._update_user_balances_from_trade(trade)

        # 添加到滚动历史记录
        self.trade_history.append(trade)
        if len(self.trade_history) > 1000:
            self.trade_history = self.trade_history[-1000:]

        return trade

    def _update_order_status(self, order: Order) -> None:
        """更新订单状态。

        Args:
            order: 要更新的订单。
        """
        if order.is_filled:
            order.status = OrderStatus.FILLED
        elif order.is_partially_filled:
            order.status = OrderStatus.PARTIALLY_FILLED

    def _update_user_balances_from_trade(self, trade: TradeSettlement) -> None:
        """根据交易记录更新用户持仓。

        Args:
            trade: 交易结算信息。
        """
        buyer = trade.buy_order.user
        seller = trade.sell_order.user
        trade_value = trade.base_amount * trade.price

        # 买家操作：获得基础资产，从锁定余额中扣除实际使用的计价资产
        buyer.update_balance(
            asset=trade.trading_pair.base_asset,
            available_change=trade.base_amount,
            locked_change=0,  # 基础资产是新获得的，不涉及锁定
        )

        # 扣除实际使用的计价资产（已成交部分对应的金额）
        actual_deduct = trade.base_amount * trade.price
        buyer.update_balance(
            asset=trade.trading_pair.quote_asset,
            available_change=0,
            locked_change=-actual_deduct,
        )

        # 卖家操作：获得计价资产，从锁定余额中扣除实际卖出的基础资产
        seller.update_balance(
            asset=trade.trading_pair.quote_asset,
            available_change=trade_value,
            locked_change=0,  # 计价资产是新获得的
        )

        # 扣除实际卖出的基础资产
        seller.update_balance(
            asset=trade.trading_pair.base_asset,
            available_change=0,
            locked_change=-trade.base_amount,
        )

    def _cleanup_filled_orders(self) -> None:
        """清理已完成的订单。"""
        self.buy_orders = [order for order in self.buy_orders if not order.is_filled]
        self.sell_orders = [order for order in self.sell_orders if not order.is_filled]

    def _update_price_from_trades(self, trades: list[TradeSettlement]) -> None:
        """根据交易更新价格。

        Args:
            trades: 交易列表。
        """
        if trades:
            # 使用最后一笔交易的价格
            self.current_price = trades[-1].price
            self.last_update = datetime.now()

    # ====================
    # 订单管理 - 从exchange迁移过来的方法
    # ====================

    # ====================
    # 订单簿操作
    # ====================

    # ====================
    # 市场数据
    # ====================

    @property
    def symbol(self) -> str:
        """交易对符号。

        Returns:
            str: 交易对符号，如"BTC/USDT"。
        """
        return f'{self.base_asset.value}/{self.quote_asset.value}'

    def get_order_book(self) -> dict[str, list[dict[str, float]]]:
        return {
            'bids': [
                {'price': order.price, 'quantity': order.remaining_base_amount}
                for order in self.buy_orders
            ],
            'asks': [
                {'price': order.price, 'quantity': order.remaining_base_amount}
                for order in self.sell_orders
            ],
        }

    def get_recent_trades(self, limit: int = 10) -> list[TradeSettlement]:
        return self.trade_history[-limit:] if self.trade_history else []

    # ====================
    # 订单放置和管理
    # ====================

    def place_order(
        self,
        user: User,
        order_type: OrderType,
        base_amount: float | None = None,
        price: float | None = None,
        quote_amount: float | None = None,
    ) -> Order:
        from .typing import Order

        self._validate_order_parameters(order_type, base_amount, price, quote_amount)
        self._validate_user_balance(user, order_type, base_amount, price, quote_amount)
        self._cancel_opposite_orders(user, order_type)

        order = Order(
            user=user,
            order_type=order_type,
            trading_pair=TradingPairType(f'{self.base_asset.value}/{self.quote_asset.value}'),
            base_amount=base_amount,
            price=price,
            quote_amount=quote_amount,
        )

        self._freeze_assets_for_order(user, order_type, base_amount, price, quote_amount)
        self._insert_order(order)
        self._match_orders()
        return order

    def _insert_buy_order_internal(self, order: Order) -> None:
        """内部方法：插入买单（价格降序）。"""
        for i, existing_order in enumerate(self.buy_orders):
            if order.price > existing_order.price:
                self.buy_orders.insert(i, order)
                return
        self.buy_orders.append(order)

    def _insert_sell_order_internal(self, order: Order) -> None:
        """内部方法：插入卖单（价格升序）。"""
        for i, existing_order in enumerate(self.sell_orders):
            if order.price < existing_order.price:
                self.sell_orders.insert(i, order)
                return
        self.sell_orders.append(order)

    def _match_orders_internal(self) -> list[TradeSettlement]:
        """内部方法：执行订单匹配。"""
        trades = []

        # 先处理市价订单
        market_trades = self._execute_market_orders_internal()
        trades.extend(market_trades)

        # 再处理限价订单匹配
        limit_trades = self._match_limit_orders_internal()
        trades.extend(limit_trades)

        # 更新价格
        if trades:
            self._update_price_from_trades(trades)

        return trades

    def _execute_market_orders_internal(self) -> list[TradeSettlement]:
        """内部方法：执行市价订单。"""
        trades = []

        # 处理市价买单
        for market_buy in self.market_buy_orders[:]:
            trades.extend(self._execute_market_buy_internal(market_buy))

        # 处理市价卖单
        for market_sell in self.market_sell_orders[:]:
            trades.extend(self._execute_market_sell_internal(market_sell))

        return trades

    def _execute_market_buy_internal(self, market_buy: Order) -> list[TradeSettlement]:
        """内部方法：执行市价买单。"""
        trades = []
        remaining_amount = market_buy.quote_amount
        if remaining_amount is None:
            # 如果指定了base_amount，使用base_amount计算
            if market_buy.base_amount is not None:
                remaining_amount = market_buy.base_amount * self.current_price
            else:
                return trades

        # 从卖单簿中按价格从低到高成交
        for sell_order in self.sell_orders[:]:
            if remaining_amount <= 0 or market_buy.is_filled:
                break

            available_quantity = sell_order.remaining_base_amount
            trade_price = sell_order.price
            max_quantity = remaining_amount / trade_price
            trade_quantity = min(available_quantity, max_quantity)

            if trade_quantity > 0:
                trade = self._create_trade(market_buy, sell_order, trade_quantity, trade_price)
                if trade is not None:
                    trades.append(trade)
                    remaining_amount -= trade_quantity * trade_price

        return trades

    def _execute_market_sell_internal(self, market_sell: Order) -> list[TradeSettlement]:
        """内部方法：执行市价卖单。"""
        trades = []
        remaining_quantity = market_sell.base_amount
        if remaining_quantity is None:
            # 如果指定了quote_amount，使用quote_amount计算
            if market_sell.quote_amount is not None:
                remaining_quantity = market_sell.quote_amount / self.current_price
            else:
                return trades

        # 从买单簿中按价格从高到低成交
        for buy_order in self.buy_orders[:]:
            if remaining_quantity <= 0 or market_sell.is_filled:
                break

            available_quantity = buy_order.remaining_base_amount
            trade_price = buy_order.price
            trade_quantity = min(available_quantity, remaining_quantity)

            if trade_quantity > 0:
                trade = self._create_trade(buy_order, market_sell, trade_quantity, trade_price)
                if trade is not None:
                    trades.append(trade)
                    remaining_quantity -= trade_quantity

        return trades

    def _match_limit_orders_internal(self) -> list[TradeSettlement]:
        """内部方法：匹配限价订单。"""
        trades = []

        while self.buy_orders and self.sell_orders:
            best_buy = self.buy_orders[0]
            best_sell = self.sell_orders[0]

            # 检查是否可以成交
            if best_buy.price >= best_sell.price:
                trade_quantity = min(
                    best_buy.remaining_base_amount, best_sell.remaining_base_amount
                )
                trade_price = best_sell.price  # 按卖单价格成交

                trade = self._create_trade(best_buy, best_sell, trade_quantity, trade_price)
                if trade is not None:
                    trades.append(trade)

                # 清理已完成的订单
                self._cleanup_filled_orders_internal()
            else:
                break

        return trades

    def _cleanup_filled_orders_internal(self) -> None:
        """内部方法：清理已完成的订单。"""
        self.buy_orders = [order for order in self.buy_orders if not order.is_filled]
        self.sell_orders = [order for order in self.sell_orders if not order.is_filled]
        self.market_buy_orders = [order for order in self.market_buy_orders if not order.is_filled]
        self.market_sell_orders = [
            order for order in self.market_sell_orders if not order.is_filled
        ]

    def _update_price_from_trades(self, trades: list[TradeSettlement]) -> None:
        """根据交易更新价格。"""
        if trades:
            # 使用最后一笔交易的价格
            self.current_price = trades[-1].price
            self.last_update = datetime.now()

    def cancel_order(self, order: Order) -> bool:
        if order.is_filled:
            return False
        removed = self._remove_order(order)
        if removed:
            self._release_frozen_assets(order.user, order)
            order.status = OrderStatus.CANCELLED
        return removed

    def _validate_order_parameters(
        self,
        order_type: OrderType,
        base_amount: float | None,
        price: float | None,
        quote_amount: float | None,
    ) -> None:
        """验证订单参数。

        Args:
            order_type: 订单类型
            base_amount: 基础资产数量
            price: 订单价格
            quote_amount: 计价资产金额

        Raises:
            ValueError: 参数不合法
        """
        if order_type in [OrderType.BUY, OrderType.SELL] and (price is None or price <= 0):
            raise ValueError('限价订单必须指定有效价格')

        if base_amount is None and quote_amount is None:
            raise ValueError('订单必须指定基础资产数量或计价资产金额')

        if base_amount is not None and base_amount <= 0:
            raise ValueError('基础资产数量必须大于0')

        if quote_amount is not None and quote_amount <= 0:
            raise ValueError('计价资产金额必须大于0')

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

    def _freeze_assets_for_order(
        self,
        user: User,
        order_type: OrderType,
        base_amount: float | None,
        price: float | None,
        quote_amount: float | None,
    ) -> None:
        """冻结订单所需的资产。

        Args:
            user: 用户对象
            order_type: 订单类型
            base_amount: 基础资产数量
            price: 订单价格
            quote_amount: 计价资产金额
        """
        if order_type in [OrderType.BUY, OrderType.MARKET_BUY]:
            # 买单冻结计价资产
            if order_type == OrderType.MARKET_BUY:
                if quote_amount is not None:
                    freeze_amount = quote_amount
                elif base_amount is not None:
                    freeze_amount = base_amount * self.current_price
                else:
                    freeze_amount = 0
            else:  # 限价买单
                if base_amount is not None and price is not None:
                    freeze_amount = base_amount * price
                elif quote_amount is not None:
                    freeze_amount = quote_amount
                else:
                    freeze_amount = 0

            user.update_balance(
                asset=self.quote_asset,
                available_change=-freeze_amount,
                locked_change=freeze_amount,
            )

        else:  # 卖单冻结基础资产
            if order_type == OrderType.MARKET_SELL:
                if base_amount is not None:
                    freeze_amount = base_amount
                elif quote_amount is not None:
                    freeze_amount = quote_amount / self.current_price
                else:
                    freeze_amount = 0
            else:  # 限价卖单
                if base_amount is not None:
                    freeze_amount = base_amount
                elif quote_amount is not None and price is not None:
                    freeze_amount = quote_amount / price
                else:
                    freeze_amount = 0

            user.update_balance(
                asset=self.base_asset,
                available_change=-freeze_amount,
                locked_change=freeze_amount,
            )

    def _release_frozen_assets(self, user: User, order: Order) -> None:
        """释放订单冻结的资产。

        Args:
            user: 用户对象
            order: 要取消的订单
        """
        if order.order_type in [OrderType.BUY, OrderType.MARKET_BUY]:
            # 释放未使用的计价资产
            remaining_quote = 0.0
            if order.base_amount is not None and order.price is not None:
                total_quote = order.base_amount * order.price
                used_quote = order.filled_base_amount * order.price
                remaining_quote = total_quote - used_quote
            elif order.quote_amount is not None:
                remaining_quote = order.quote_amount - order.filled_quote_amount

            if remaining_quote > 0:
                user.update_balance(
                    asset=self.quote_asset,
                    available_change=remaining_quote,
                    locked_change=-remaining_quote,
                )

        else:  # 卖单
            # 释放未卖出的基础资产
            remaining_base = 0.0
            if order.base_amount is not None:
                remaining_base = order.base_amount - order.filled_base_amount
            elif order.quote_amount is not None and order.price is not None:
                total_base = order.quote_amount / order.price
                used_base = order.filled_quote_amount / order.price
                remaining_base = total_base - used_base

            if remaining_base > 0:
                user.update_balance(
                    asset=self.base_asset,
                    available_change=remaining_base,
                    locked_change=-remaining_base,
                )

    def _cancel_opposite_orders(self, user: User, new_order_type: OrderType) -> None:
        """撤销用户当前资产的相反方向订单。

        Args:
            user: 用户对象
            new_order_type: 新订单类型
        """
        # 确定相反方向的订单类型（只处理限价订单，因为市价订单会立即执行）
        opposite_types = []
        if new_order_type == OrderType.BUY:
            opposite_types = [OrderType.SELL]
        elif new_order_type == OrderType.SELL:
            opposite_types = [OrderType.BUY]
        elif new_order_type == OrderType.MARKET_BUY:
            opposite_types = [OrderType.SELL]
        elif new_order_type == OrderType.MARKET_SELL:
            opposite_types = [OrderType.BUY]

        # 获取用户的相反方向订单（只处理限价订单）
        opposite_orders = [
            order
            for order in self.buy_orders + self.sell_orders
            if order.user.id == user.id
            and order.order_type in opposite_types
            and order.status in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]
        ]

        # 撤销这些订单
        for order in opposite_orders:
            try:
                removed = self.cancel_order(order)
                if removed:
                    # 释放冻结的资产已在内cancel_order中处理
                    pass
            except ValueError:
                pass  # 忽略撤销失败的情况
