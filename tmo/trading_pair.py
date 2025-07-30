"""交易对核心逻辑。

该模块实现了交易对引擎，负责管理订单簿、执行交易撮合、处理订单生命周期，
以及维护价格发现和交易历史记录。
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from .constants import OrderStatus, OrderType, TradingPairType
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

        处理完整的订单生命周期：参数验证、余额检查、资产冻结、
        价格交叉检查、订单插入和自动撮合。

        用户可以同时持有买单和卖单，但不允许价格交叉（买单价格不能高于卖单价格）。

        Args:
            user: 下单用户。
            order_type: 订单类型（BUY/SELL/MARKET_BUY/MARKET_SELL）。
            base_amount: 基础资产数量，与quote_amount二选一。
            price: 订单价格，限价订单必填。
            quote_amount: 计价资产金额，与base_amount二选一。

        Returns:
            Order: 创建的订单对象，已执行撮合。

        Raises:
            ValueError: 参数不合法、余额不足或价格交叉。
        """
        # Pydantic会自动验证订单参数，这里只需要验证余额和价格交叉
        self._validate_user_balance(user, order_type, base_amount, price, quote_amount)
        self._validate_price_crossing(user, order_type, price)

        order = Order(
            user_id=user.id,
            order_type=order_type,
            trading_pair=TradingPairType(f'{self.base_asset.value}/{self.quote_asset.value}'),
            base_amount=base_amount,
            price=price,
            quote_amount=quote_amount,
        )

        self._freeze_assets_for_order(user, order_type, base_amount, price, quote_amount)
        self._insert_order(order)
        user.add_active_order(order)
        self._match_orders()
        return order

    def cancel_order(self, order: Order, user: User) -> bool:
        """取消订单。

        从订单簿中移除订单并释放冻结的资产。

        Args:
            order: 要取消的订单。

        Returns:
            bool: 取消成功返回True，失败返回False。
        """
        if order.is_filled:
            return False
        removed = self._remove_order(order)
        if removed:
            self._release_frozen_assets(user, order)
            order.status = OrderStatus.CANCELLED
            user.move_order_to_completed(order)
        return removed

    def get_order_book(self) -> OrderBookSnapshot:
        """获取订单簿快照。

        Returns:
            OrderBookSnapshot: 订单簿快照，包含买单和卖单信息。
        """
        bids = [
            OrderBookLevel(price=order.price, quantity=order.remaining_base_amount)
            for order in self.orders[OrderType.BUY]
        ]
        asks = [
            OrderBookLevel(price=order.price, quantity=order.remaining_base_amount)
            for order in self.orders[OrderType.SELL]
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

    @property
    def symbol(self) -> str:
        """交易对符号。

        Returns:
            str: 交易对符号，如"BTC/USDT"。
        """
        return f'{self.base_asset.value}/{self.quote_asset.value}'

    @property
    def buy_orders(self) -> list[Order]:
        """获取所有限价买单。

        Returns:
            list[Order]: 按价格降序排列的限价买单列表。
        """
        return self.orders[OrderType.BUY]

    @property
    def sell_orders(self) -> list[Order]:
        """获取所有限价卖单。

        Returns:
            list[Order]: 按价格升序排列的限价卖单列表。
        """
        return self.orders[OrderType.SELL]

    @property
    def market_buy_orders(self) -> list[Order]:
        """获取所有市价买单。

        Returns:
            list[Order]: 市价买单列表。
        """
        return self.orders[OrderType.MARKET_BUY]

    @property
    def market_sell_orders(self) -> list[Order]:
        """获取所有市价卖单。

        Returns:
            list[Order]: 市价卖单列表。
        """
        return self.orders[OrderType.MARKET_SELL]

    # ====================
    # 订单管理内部方法
    # ====================

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

        从卖单簿中按价格从低到高成交。

        Args:
            market_buy: 市价买单。

        Returns:
            list: 生成的交易记录列表。
        """
        trades = []
        max_trades = 1000  # 防止无限循环
        trades_count = 0

        # 获取原始冻结的计价资产金额
        original_quote = market_buy.quote_amount
        if original_quote is None:
            if market_buy.base_amount is not None:
                original_quote = market_buy.base_amount * self.current_price
            else:
                return trades

        # 计算已成交的计价资产金额和剩余
        executed_quote = market_buy.filled_quote_amount
        remaining_quote = original_quote - executed_quote

        if remaining_quote <= 0:
            return trades

        # 从卖单簿中按价格从低到高成交
        for sell_order in self.orders[OrderType.SELL][:]:
            if trades_count >= max_trades:
                break

            if remaining_quote <= 1e-10 or market_buy.is_filled:
                break

            available_quantity = sell_order.remaining_base_amount
            trade_price = sell_order.price
            max_quantity = remaining_quote / trade_price
            trade_quantity = min(available_quantity, max_quantity)

            if trade_quantity > 1e-10:
                actual_quote = trade_quantity * trade_price
                # 确保不超过剩余冻结金额
                actual_quote = min(actual_quote, remaining_quote)
                trade_quantity = actual_quote / trade_price

                trade = self._create_trade(market_buy, sell_order, trade_quantity, trade_price)
                if trade is not None:
                    trades.append(trade)
                    remaining_quote -= actual_quote
                    trades_count += 1
            else:
                break

        return trades

    def _execute_market_sell(self, market_sell: Order) -> list[TradeSettlement]:
        """执行单个市价卖单。

        从买单簿中按价格从高到低成交。

        Args:
            market_sell: 市价卖单。

        Returns:
            list: 生成的交易记录列表。
        """
        trades = []
        max_trades = 1000  # 防止无限循环
        trades_count = 0

        # 获取原始冻结的基础资产数量
        original_base = market_sell.base_amount
        if original_base is None:
            if market_sell.quote_amount is not None:
                original_base = market_sell.quote_amount / self.current_price
            else:
                return trades

        # 计算已成交的基础资产数量和剩余
        executed_base = market_sell.filled_base_amount
        remaining_base = original_base - executed_base

        if remaining_base <= 0:
            return trades

        # 从买单簿中按价格从高到低成交
        for buy_order in self.orders[OrderType.BUY][:]:
            if trades_count >= max_trades:
                break

            if remaining_base <= 1e-10 or market_sell.is_filled:
                break

            available_quantity = buy_order.remaining_base_amount
            trade_price = buy_order.price
            trade_quantity = min(available_quantity, remaining_base)

            if trade_quantity > 1e-10:
                # 确保不超过剩余冻结数量
                trade_quantity = min(trade_quantity, remaining_base)

                trade = self._create_trade(buy_order, market_sell, trade_quantity, trade_price)
                if trade is not None:
                    trades.append(trade)
                    remaining_base -= trade_quantity
                    trades_count += 1
            else:
                break

        return trades

    def _match_limit_orders(self) -> list[TradeSettlement]:
        """匹配限价订单。

        采用价格-时间优先算法匹配买单和卖单。

        Returns:
            list: 生成的交易记录列表。
        """
        trades = []
        max_iterations = 1000  # 防止无限循环
        iterations = 0

        while (
            self.orders[OrderType.BUY]
            and self.orders[OrderType.SELL]
            and iterations < max_iterations
        ):
            iterations += 1
            best_buy = self.orders[OrderType.BUY][0]
            best_sell = self.orders[OrderType.SELL][0]

            # 检查是否可以成交（考虑浮点数精度）
            if best_buy.price >= best_sell.price - 1e-10:  # 添加epsilon容差
                trade_quantity = min(
                    best_buy.remaining_base_amount, best_sell.remaining_base_amount
                )

                # 确保交易数量大于最小阈值
                if trade_quantity <= 1e-10:
                    break

                trade_price = best_sell.price  # 按卖单价格成交

                trade = self._create_trade(best_buy, best_sell, trade_quantity, trade_price)
                if trade is not None:
                    trades.append(trade)

                # 清理已完成的订单
                self._cleanup_filled_orders()

                # 如果没有任何订单被清理，说明可能有精度问题，退出循环
                if not any(order.is_filled for order in [best_buy, best_sell]):
                    break
            else:
                break

        return trades

    def _cleanup_filled_orders(self) -> None:
        """清理已完成的订单。

        从订单簿中移除已完全成交的订单。
        """
        self.orders[OrderType.BUY] = [
            order for order in self.orders[OrderType.BUY] if not order.is_filled
        ]
        self.orders[OrderType.SELL] = [
            order for order in self.orders[OrderType.SELL] if not order.is_filled
        ]
        self.orders[OrderType.MARKET_BUY] = [
            order for order in self.orders[OrderType.MARKET_BUY] if not order.is_filled
        ]
        self.orders[OrderType.MARKET_SELL] = [
            order for order in self.orders[OrderType.MARKET_SELL] if not order.is_filled
        ]

    # ====================
    # 交易创建和更新方法
    # ====================

    def _create_trade(
        self,
        buy_order: Order,
        sell_order: Order,
        quantity: float,
        price: float,
    ) -> TradeSettlement | None:
        """创建交易记录。

        根据买卖订单和成交信息创建交易记录，更新订单状态，
        并处理用户余额更新。

        Args:
            buy_order: 买单对象。
            sell_order: 卖单对象。
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

        # 更新买卖双方的持仓
        self._update_user_balances_from_trade(trade)

        # 更新用户订单状态
        # Note: We need to get the actual users from the exchange to move orders
        # This will be handled by the exchange layer

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

    # ====================
    # 验证和余额处理方法
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

    def _freeze_assets_for_order(
        self,
        user: User,
        order_type: OrderType,
        base_amount: float | None,
        price: float | None,
        quote_amount: float | None,
    ) -> None:
        """验证订单所需的资产是否充足。

        在新的系统中，不再冻结资产，仅验证可用余额是否充足。
        锁定金额通过活跃订单动态计算。

        Args:
            user: 用户对象
            order_type: 订单类型
            base_amount: 基础资产数量
            price: 订单价格
            quote_amount: 计价资产金额
        """
        # 此方法现在仅用于验证，不执行实际的冻结操作

    def _release_frozen_assets(self, user: User, order: Order) -> None:
        """释放订单冻结的资产。

        在新的系统中，不再使用锁定余额机制，可用余额通过活跃订单动态计算。
        此方法现在仅用于保持接口一致性，不执行实际的资产释放操作。

        Args:
            user: 用户对象
            order: 要取消的订单
        """
        # 在新的系统中，资产释放通过移除活跃订单自动处理

    def _validate_price_crossing(
        self, user: User, order_type: OrderType, price: float | None
    ) -> None:
        """验证价格交叉。

        检查用户是否尝试创建价格交叉的订单：
        - 买单价格不能高于用户已有的卖单价格（严格大于）
        - 卖单价格不能低于用户已有的买单价格（严格小于）

        Args:
            user: 用户对象
            order_type: 订单类型
            price: 订单价格（限价订单）

        Raises:
            ValueError: 如果检测到价格交叉
        """
        if price is None:
            return  # 市价订单不检查价格交叉

        trading_pair_type = TradingPairType(f'{self.base_asset.value}/{self.quote_asset.value}')

        if order_type == OrderType.BUY:
            # 检查是否有卖单价格严格低于新的买单价格
            user_sell_orders = user.get_active_orders(trading_pair_type, OrderType.SELL)
            for sell_order in user_sell_orders:
                if sell_order.price is not None and price > sell_order.price:
                    raise ValueError(
                        f'价格交叉：买单价格 {price} 不能高于卖单价格 {sell_order.price}'
                    )

        elif order_type == OrderType.SELL:
            # 检查是否有买单价格严格高于新的卖单价格
            user_buy_orders = user.get_active_orders(trading_pair_type, OrderType.BUY)
            for buy_order in user_buy_orders:
                if buy_order.price is not None and price < buy_order.price:
                    raise ValueError(
                        f'价格交叉：卖单价格 {price} 不能低于买单价格 {buy_order.price}'
                    )
