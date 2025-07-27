"""交易对核心逻辑。

该模块实现了交易对的完整功能，包括订单管理、交易撮合、价格更新和市场数据提供。
每个交易对独立管理自己的订单簿和交易历史。
"""

from __future__ import annotations

from datetime import datetime

from .constants import OrderStatus, OrderType, TradingPairType
from .typing import Order, TradeSettlement


class TradingPairEngine:
    """交易对引擎。

    管理单个交易对的订单簿、交易撮合和价格更新。
    支持限价单和市价单的撮合，提供完整的市场数据。

    Attributes:
        base_asset: 基础资产类型，如BTC。
        quote_asset: 计价资产类型，如USDT。
        current_price: 当前市场价格。
        last_update: 最后更新时间。
        buy_orders: 限价买单列表，按价格降序排列。
        sell_orders: 限价卖单列表，按价格升序排列。
        market_buy_orders: 市价买单列表。
        market_sell_orders: 市价卖单列表。
        trade_history: 交易历史记录。
    """

    def __init__(
        self,
        trading_pair_type: TradingPairType,
    ):
        """初始化交易对。

        Args:
            trading_pair_type: 交易对类型枚举。
        """
        self.base_asset = trading_pair_type.base_asset
        self.quote_asset = trading_pair_type.quote_asset
        self.current_price = trading_pair_type.initial_price
        self.last_update = datetime.now()

        # 订单簿
        self.buy_orders: list[Order] = []  # 限价买单，价格降序
        self.sell_orders: list[Order] = []  # 限价卖单，价格升序
        self.market_buy_orders: list[Order] = []  # 市价买单
        self.market_sell_orders: list[Order] = []  # 市价卖单

        # 交易历史
        self.trade_history: list[TradeSettlement] = []

    # ====================
    # 订单管理
    # ====================

    def add_order(self, order: Order) -> None:
        """添加订单到订单簿。

        Args:
            order: 要添加的订单。
        """
        if order.order_type == OrderType.BUY:
            self._insert_buy_order(order)
        elif order.order_type == OrderType.SELL:
            self._insert_sell_order(order)
        elif order.order_type == OrderType.MARKET_BUY:
            self.market_buy_orders.append(order)
        elif order.order_type == OrderType.MARKET_SELL:
            self.market_sell_orders.append(order)

    def remove_order(self, order: Order) -> bool:
        """从订单簿移除订单。

        Args:
            order: 要移除的订单。

        Returns:
            bool: 成功移除返回True，否则返回False。
        """
        if order.order_type == OrderType.BUY and order in self.buy_orders:
            self.buy_orders.remove(order)
            return True
        elif order.order_type == OrderType.SELL and order in self.sell_orders:
            self.sell_orders.remove(order)
            return True
        elif order.order_type == OrderType.MARKET_BUY and order in self.market_buy_orders:
            self.market_buy_orders.remove(order)
            return True
        elif order.order_type == OrderType.MARKET_SELL and order in self.market_sell_orders:
            self.market_sell_orders.remove(order)
            return True
        return False

    # ====================
    # 交易撮合
    # ====================

    def match_orders(self) -> list[TradeSettlement]:
        """执行订单匹配。

        Returns:
            List[TradeSettlement]: 本次匹配产生的交易列表。
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

        return trades

    def _execute_market_orders(self) -> list[TradeSettlement]:
        """执行市价订单。

        Returns:
            List[TradeSettlement]: 市价订单交易列表。
        """
        trades = []

        # 处理市价买单
        for market_buy in self.market_buy_orders[:]:
            trades.extend(self._execute_market_buy(market_buy))

        # 处理市价卖单
        for market_sell in self.market_sell_orders[:]:
            trades.extend(self._execute_market_sell(market_sell))

        return trades

    def _execute_market_buy(self, market_buy: Order) -> list[TradeSettlement]:
        """执行市价买单。

        Args:
            market_buy: 市价买单。

        Returns:
            List[TradeSettlement]: 交易列表。
        """
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

    def _execute_market_sell(self, market_sell: Order) -> list[TradeSettlement]:
        """执行市价卖单。

        Args:
            market_sell: 市价卖单。

        Returns:
            List[TradeSettlement]: 交易列表。
        """
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

    def _match_limit_orders(self) -> list[TradeSettlement]:
        """匹配限价订单。

        Returns:
            List[TradeSettlement]: 交易列表。
        """
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
                self._cleanup_filled_orders()
            else:
                break

        return trades

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

        # 买家操作：获得基础资产，从锁定余额中扣除计价资产
        buyer.update_balance(
            asset=trade.trading_pair.base_asset,
            available_change=trade.base_amount,
            locked_change=0,  # 基础资产是新获得的，不涉及锁定
        )
        buyer.update_balance(
            asset=trade.trading_pair.quote_asset,
            available_change=0,  # 计价资产从锁定余额中扣除
            locked_change=-trade.base_amount * trade.price,
        )

        # 卖家操作：获得计价资产，从锁定余额中扣除基础资产
        seller.update_balance(
            asset=trade.trading_pair.quote_asset,
            available_change=trade.base_amount * trade.price,
            locked_change=0,  # 计价资产是新获得的
        )
        seller.update_balance(
            asset=trade.trading_pair.base_asset,
            available_change=0,  # 基础资产从锁定余额中扣除
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
    # 订单簿操作
    # ====================

    def _insert_buy_order(self, order: Order) -> None:
        """插入买单（价格降序）。

        Args:
            order: 要插入的买单。
        """
        for i, existing_order in enumerate(self.buy_orders):
            if order.price > existing_order.price:
                self.buy_orders.insert(i, order)
                return
        self.buy_orders.append(order)

    def _insert_sell_order(self, order: Order) -> None:
        """插入卖单（价格升序）。

        Args:
            order: 要插入的卖单。
        """
        for i, existing_order in enumerate(self.sell_orders):
            if order.price < existing_order.price:
                self.sell_orders.insert(i, order)
                return
        self.sell_orders.append(order)

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
        """获取订单簿。

        Returns:
            Dict[str, List[Dict[str, float]]]: 订单簿数据。
        """
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
        """获取最近的成交记录。

        Args:
            limit: 返回记录数量限制。

        Returns:
            List[TradeSettlement]: 最近的成交记录。
        """
        return self.trade_history[-limit:] if self.trade_history else []

    def get_market_summary(self) -> dict[str, any]:
        """获取市场摘要。

        Returns:
            Dict[str, any]: 市场摘要信息。
        """
        return {
            'symbol': self.symbol,
            'current_price': self.current_price,
            'last_update': self.last_update,
            'total_bids': len(self.buy_orders),
            'total_asks': len(self.sell_orders),
            'recent_trades': len(self.trade_history),
            'best_bid': self.buy_orders[0].price if self.buy_orders else None,
            'best_ask': self.sell_orders[0].price if self.sell_orders else None,
        }
