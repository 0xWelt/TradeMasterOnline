"""模拟交易所核心逻辑。

该模块实现了完整的交易所功能，包括订单管理、交易撮合、资产管理和市场数据提供。
支持限价订单、市价订单，提供实时价格更新和用户余额管理。
"""

from __future__ import annotations

from datetime import datetime

from loguru import logger

from .constants import AssetType, OrderStatus, OrderType, TradingPairType
from .trading_pair import TradingPairEngine
from .typing import Asset, Order, Portfolio, TradeSettlement, User


class Exchange:
    """模拟交易所 - 提供完整的交易撮合系统。

    实现了一个功能完整的数字资产交易所，支持多种交易对和订单类型。
    提供订单管理、交易撮合、资产管理和市场数据查询等功能。

    Attributes:
        assets: 支持的资产字典，包含所有可交易资产的详细信息。
        trading_pairs: 交易对字典，包含所有可交易交易对的当前价格和基本信息。
        order_books: 订单簿，按交易对和订单类型组织所有待成交订单。
        trade_settlements: 交易结算记录列表，保存所有历史成交信息。
        orders: 订单索引字典，通过订单ID快速查找订单。
        users: 用户字典，保存所有注册用户的信息。
    """

    def __init__(self):
        """初始化交易所。

        设置交易所的初始状态，包括：
        - 创建默认资产（USDT、BTC、ETH）
        - 初始化交易对和初始价格
        - 设置空的订单簿和交易记录
        - 初始化用户管理
        """
        # 支持的资产
        self.assets: dict[AssetType, Asset] = {
            AssetType.USDT: Asset(
                symbol=AssetType.USDT, name='Tether USD', description='美元稳定币'
            ),
            AssetType.BTC: Asset(symbol=AssetType.BTC, name='Bitcoin', description='比特币'),
            AssetType.ETH: Asset(symbol=AssetType.ETH, name='Ethereum', description='以太坊'),
        }

        # 交易对引擎 - 使用新的TradingPair类管理每个交易对
        self.trading_pair_engines: dict[str, TradingPairEngine] = {
            pair.value: TradingPairEngine(trading_pair_type=pair) for pair in TradingPairType
        }

        # 交易结算记录
        self.trade_settlements: list[TradeSettlement] = []

        # 订单索引
        self.orders: dict[str, Order] = {}

        # 用户管理
        self.users: dict[str, User] = {}

    # ====================
    # 用户管理 - 新增功能
    # ====================

    def create_user(self, username: str, email: str) -> User:
        """创建新用户。

        创建一个新的交易所用户，初始化用户的资产持仓信息。
        每个新用户初始获得1000 USDT的余额，其他资产余额为0。

        Args:
            username: 用户名，必须唯一。
            email: 用户邮箱地址。

        Returns:
            User: 新创建的用户对象。

        Raises:
            ValueError: 如果用户名已存在。

        Example:
            >>> exchange = Exchange()
            >>> user = exchange.create_user("alice", "alice@example.com")
            >>> print(user.username)  # 输出: alice
        """
        # 检查用户名是否已存在
        for existing_user in self.users.values():
            if existing_user.username == username:
                raise ValueError(f'用户名已存在: {username}')

        user = User(username=username, email=email)

        # 初始化用户持仓
        for asset_type in self.assets:
            user.portfolios[asset_type] = Portfolio(
                asset=asset_type,
                available_balance=1000.0 if asset_type == AssetType.USDT else 0.0,  # 初始USDT余额
                locked_balance=0.0,
            )

        self.users[user.id] = user
        logger.debug(f'创建用户: {username} ({email}) - 初始USDT余额: 1000.0')
        return user

    def get_user(self, user_id: str) -> User | None:
        """获取用户信息。

        根据用户ID查找并返回对应的用户对象。

        Args:
            user_id: 用户的唯一标识符。

        Returns:
            User | None: 找到的用户对象，如果用户不存在则返回None。
        """
        return self.users.get(user_id)

    def list_users(self) -> list[User]:
        """获取所有用户列表。

        返回系统中所有注册用户的列表。

        Returns:
            list[User]: 包含所有用户对象的列表。
        """
        return list(self.users.values())

    def get_user_portfolio(self, user: User, asset: AssetType) -> Portfolio:
        """获取用户特定资产的持仓。

        返回用户在指定资产上的持仓信息，包括可用余额、锁定余额和总余额。

        Args:
            user: 要查询的用户对象。
            asset: 要查询的资产类型。

        Returns:
            Portfolio: 用户在指定资产上的持仓信息。
        """
        return user.portfolios[asset]

    def get_user_portfolios(self, user: User) -> dict[AssetType, Portfolio]:
        """获取用户所有持仓。

        返回用户在所有资产上的持仓信息字典。

        Args:
            user: 要查询的用户对象。

        Returns:
            dict[AssetType, Portfolio]: 键为资产类型，值为对应持仓信息的字典。
        """
        return user.portfolios

    # ====================
    # 资产操作 - 新增功能
    # ====================

    def deposit(self, user: User, asset: AssetType, amount: float) -> None:
        """用户充值。

        为用户指定资产增加可用余额，模拟用户充值资产到交易所。

        Args:
            user: 要充值的用户对象。
            asset: 要充值的资产类型。
            amount: 充值金额，必须大于0。

        Raises:
            ValueError: 如果充值金额小于等于0。
        """
        if amount <= 0:
            raise ValueError('充值金额必须大于0')

        portfolio = user.portfolios[asset]
        portfolio.available_balance += amount

        logger.debug(f'用户 {user.username} 充值 {amount} {asset.value}')

    def withdraw(self, user: User, asset: AssetType, amount: float) -> None:
        """用户提现。

        从用户指定资产的可用余额中扣除相应金额，模拟用户从交易所提现。

        Args:
            user: 要提现的用户对象。
            asset: 要提现的资产类型。
            amount: 提现金额，必须大于0。

        Raises:
            ValueError: 如果提现金额小于等于0，或用户可用余额不足。
        """
        if amount <= 0:
            raise ValueError('提现金额必须大于0')

        portfolio = user.portfolios[asset]
        if portfolio.available_balance < amount:
            raise ValueError('可用余额不足')

        portfolio.available_balance -= amount

        logger.debug(f'用户 {user.username} 提现 {amount} {asset.value}')

    # ====================
    # 操作接口 - 订单管理
    # ====================

    def place_order(
        self,
        user: User,
        order_type: OrderType,
        trading_pair: TradingPairType,
        base_amount: float | None = None,
        price: float | None = None,
        quote_amount: float | None = None,
    ) -> Order:
        """下单并立即执行匹配"""
        # 验证用户合法性
        if user.id not in self.users or user != self.users[user.id]:
            raise ValueError('无效用户或用户对象不一致')

        # 验证交易对类型
        if trading_pair.value not in self.trading_pair_engines:
            raise ValueError(f'不支持的交易对: {trading_pair.value}')

        # 处理单边持仓逻辑：撤销相反方向的订单
        self._cancel_opposite_orders(user, trading_pair, order_type)

        # 验证用户持仓（现在由Order模型自动验证参数合理性）
        self._validate_order_balance(
            user, order_type, trading_pair, base_amount, price, quote_amount
        )

        # 处理市价订单
        if order_type in [OrderType.MARKET_BUY, OrderType.MARKET_SELL]:
            return self._place_market_order(
                user, order_type, trading_pair, base_amount=base_amount, quote_amount=quote_amount
            )

        order = Order(
            user=user,
            order_type=order_type,
            trading_pair=trading_pair,
            base_amount=base_amount,
            price=price,
            quote_amount=quote_amount,
        )

        # 冻结相应资产
        if order_type == OrderType.BUY:
            # 买单锁定计价资产
            if order.base_amount is not None and order.price is not None:
                required_quote = order.base_amount * order.price
            elif order.quote_amount is not None:
                required_quote = order.quote_amount
            else:
                required_quote = 0.0

            user.update_balance(
                asset=trading_pair.quote_asset,
                available_change=-required_quote,
                locked_change=required_quote,
            )
        else:
            # 卖单锁定基础资产
            if order.base_amount is not None:
                required_base = order.base_amount
            else:
                # 对于使用quote_amount的卖单，需要计算基础资产数量
                # 这种情况应在交易引擎中处理
                required_base = 0.0

            user.update_balance(
                asset=trading_pair.base_asset,
                available_change=-required_base,
                locked_change=required_base,
            )

        # 记录订单信息
        amount_str = (
            f'{order.base_amount}' if order.base_amount is not None else f'{order.quote_amount}'
        )
        price_str = f' @ ${order.price:,.2f}' if order.price is not None else ''
        logger.debug(
            f'用户 {user.username} 下 {order_type.value} 单: {amount_str} {trading_pair.value}{price_str}'
        )

        # 存储订单
        self.orders[order.id] = order

        # 使用交易对引擎处理订单
        pair_symbol = trading_pair.value
        trading_pair_engine = self.trading_pair_engines[pair_symbol]

        # 添加订单到交易对引擎
        trading_pair_engine.add_order(order)

        # 执行订单匹配并处理交易
        trades = trading_pair_engine.match_orders()

        # 交易结算已移动到TradingPairEngine层面处理，仅收集交易记录
        self.trade_settlements.extend(trades)

        # 更新交易对价格
        for trade in trades:
            self._update_trading_pair_price(pair_symbol, trade.price)

        return order

    def cancel_order(self, user: User, order_id: str) -> bool:
        """取消订单"""
        # 验证用户合法性
        if user.id not in self.users or user != self.users[user.id]:
            raise ValueError('无效用户或用户对象不一致')

        order = self.orders.get(order_id)
        if not order or order.user.id != user.id:
            logger.debug(f'用户 {user.username} 无法取消订单 {order_id}: 订单不存在或不属于该用户')
            return False

        if order.is_filled:
            logger.debug(f'用户 {user.username} 无法取消已成交订单 {order_id}')
            return False

        # 从交易对引擎中移除订单
        pair_symbol = order.trading_pair.value
        trading_pair_engine = self.trading_pair_engines[pair_symbol]
        removed = trading_pair_engine.remove_order(order)

        if removed:
            # 释放冻结的资产
            order.on_cancelled()

            # 更新订单状态
            order.status = OrderStatus.CANCELLED
            logger.debug(
                f'用户 {user.username} 取消订单: {order.base_amount} {order.trading_pair.value} @ ${order.price:,.2f}'
            )

        return removed

    def get_user_orders(self, user: User) -> list[Order]:
        """获取用户的所有订单"""
        return [order for order in self.orders.values() if order.user.id == user.id]

    def get_user_trades(self, user: User) -> list[TradeSettlement]:
        """获取用户的所有成交记录"""
        user_orders = {order.id for order in self.get_user_orders(user)}
        return [
            settlement
            for settlement in self.trade_settlements
            if settlement.buy_order_id in user_orders or settlement.sell_order_id in user_orders
        ]

    # ====================
    # 内部持仓管理方法
    # ====================

    def _validate_order_balance(
        self,
        user: User,
        order_type: OrderType,
        trading_pair: TradingPairType,
        base_amount: float | None,
        price: float | None = None,
        quote_amount: float | None = None,
    ) -> None:
        """验证订单余额"""
        if order_type in [OrderType.BUY, OrderType.MARKET_BUY]:
            # 对于买单，需要计价资产
            if order_type == OrderType.MARKET_BUY:
                # 市价买单：可能指定quote_amount或base_amount
                if quote_amount is not None:
                    required_quote = quote_amount
                elif base_amount is not None:
                    # 如果指定了base_amount，需要估算所需quote_amount（使用当前市场价格）
                    current_price = self.get_market_price(trading_pair)
                    required_quote = base_amount * current_price
                else:
                    required_quote = 0.0
            else:
                # 限价买单：使用计算后的计价资产金额
                if base_amount is not None and price is not None:
                    required_quote = base_amount * price
                elif quote_amount is not None:
                    required_quote = quote_amount
                else:
                    required_quote = 0.0

            quote_portfolio = user.portfolios[trading_pair.quote_asset]
            if required_quote > 0 and quote_portfolio.available_balance < required_quote:
                raise ValueError(
                    f'{trading_pair.quote_asset.value}余额不足，需要 {required_quote:.2f} {trading_pair.quote_asset.value}，可用 {quote_portfolio.available_balance:.2f} {trading_pair.quote_asset.value}'
                )
        else:  # SELL or MARKET_SELL
            # 对于卖单，需要基础资产
            if order_type == OrderType.MARKET_SELL:
                # 市价卖单：可能指定base_amount或quote_amount
                if base_amount is not None:
                    required_base_amount = base_amount
                elif quote_amount is not None:
                    # 如果指定了quote_amount，需要估算所需base_amount（使用当前市场价格）
                    current_price = self.get_market_price(trading_pair)
                    required_base_amount = quote_amount / current_price
                else:
                    required_base_amount = 0.0
            else:
                # 限价卖单：使用指定的基础资产数量
                if base_amount is not None:
                    required_base_amount = base_amount
                else:
                    # 对于使用quote_amount的限价卖单，需要计算基础资产数量
                    if quote_amount is not None and price is not None:
                        required_base_amount = quote_amount / price
                    else:
                        required_base_amount = 0.0

            base_portfolio = user.portfolios[trading_pair.base_asset]
            if required_base_amount > 0 and base_portfolio.available_balance < required_base_amount:
                raise ValueError(
                    f'{trading_pair.base_asset.value}余额不足，需要 {required_base_amount} {trading_pair.base_asset.value}，可用 {base_portfolio.available_balance} {trading_pair.base_asset.value}'
                )

    def _update_balances_after_trade(
        self, buyer: User, seller: User, settlement: TradeSettlement
    ) -> None:
        """交易完成后更新余额"""
        trade_amount = settlement.base_amount * settlement.price

        # 买家获得基础资产，减少计价资产
        buyer_base = buyer.portfolios[settlement.trading_pair.base_asset]
        buyer_quote = buyer.portfolios[settlement.trading_pair.quote_asset]

        buyer_base.available_balance += settlement.base_amount
        buyer_base.total_balance += settlement.base_amount

        buyer_quote.available_balance -= trade_amount
        buyer_quote.locked_balance -= trade_amount
        buyer_quote.total_balance -= trade_amount

        # 卖家获得计价资产，减少基础资产
        seller_base = seller.portfolios[settlement.trading_pair.base_asset]
        seller_quote = seller.portfolios[settlement.trading_pair.quote_asset]

        seller_quote.available_balance += trade_amount
        seller_quote.total_balance += trade_amount

        seller_base.locked_balance -= settlement.base_amount
        seller_base.total_balance -= settlement.base_amount

    # ====================
    # 状态快照接口
    # ====================

    def get_state_snapshot(self) -> dict:
        """获取交易所完整状态快照"""
        return {
            'assets': self.assets.copy(),
            'trading_pair_engines': {
                symbol: {
                    'buy_orders': [order.model_dump() for order in engine.buy_orders],
                    'sell_orders': [order.model_dump() for order in engine.sell_orders],
                    'market_buy_orders': [order.model_dump() for order in engine.market_buy_orders],
                    'market_sell_orders': [
                        order.model_dump() for order in engine.market_sell_orders
                    ],
                    'trade_history': [trade.model_dump() for trade in engine.trade_history],
                    'current_price': engine.current_price,
                    'last_update': engine.last_update,
                }
                for symbol, engine in self.trading_pair_engines.items()
            },
            'trades': [settlement.model_dump() for settlement in self.trade_settlements],
            'orders': {order_id: order.model_dump() for order_id, order in self.orders.items()},
            'users': {user_id: user.model_dump() for user_id, user in self.users.items()},
        }

    # ====================
    # 查询接口
    # ====================

    def get_market_price(self, trading_pair: TradingPairType) -> float:
        """获取交易对当前市场价格"""
        pair_symbol = trading_pair.value
        if pair_symbol in self.trading_pair_engines:
            return self.trading_pair_engines[pair_symbol].current_price
        raise ValueError(f'不存在的交易对: {pair_symbol}')

    def get_market_depth(self, trading_pair: TradingPairType) -> dict:
        """获取交易对市场深度信息"""
        pair_symbol = trading_pair.value
        if pair_symbol in self.trading_pair_engines:
            return self.trading_pair_engines[pair_symbol].get_order_book()
        return {'bids': [], 'asks': []}

    def get_market_summary(self, trading_pair: TradingPairType) -> dict:
        """获取交易对市场摘要"""
        pair_symbol = trading_pair.value
        if pair_symbol not in self.trading_pair_engines:
            raise ValueError(f'不存在的交易对: {pair_symbol}')

        engine = self.trading_pair_engines[pair_symbol]
        recent_trades = self._get_recent_trades_for_trading_pair(trading_pair, limit=50)

        # 从交易对引擎获取市场摘要
        engine_summary = engine.get_market_summary()

        return {
            'symbol': pair_symbol,
            'current_price': engine.current_price,
            'last_update': engine.last_update,
            'total_bids': engine_summary['total_bids'],
            'total_asks': engine_summary['total_asks'],
            'recent_trades': len(recent_trades),
            'best_bid': engine_summary['best_bid'],
            'best_ask': engine_summary['best_ask'],
        }

    def get_order_book(self, trading_pair: TradingPairType) -> dict[OrderType, list[Order]]:
        """获取订单簿"""
        pair_symbol = trading_pair.value
        if pair_symbol in self.trading_pair_engines:
            engine = self.trading_pair_engines[pair_symbol]

            # 获取引擎中的订单
            buy_orders = engine.buy_orders
            sell_orders = engine.sell_orders

            return {
                OrderType.BUY: buy_orders.copy(),
                OrderType.SELL: sell_orders.copy(),
            }
        return {OrderType.BUY: [], OrderType.SELL: []}

    def get_trading_pair(self, trading_pair: TradingPairType) -> dict | None:
        """获取交易对信息"""
        pair_symbol = trading_pair.value
        if pair_symbol in self.trading_pair_engines:
            engine = self.trading_pair_engines[pair_symbol]
            return {
                'base_asset': engine.base_asset,
                'quote_asset': engine.quote_asset,
                'current_price': engine.current_price,
                'last_update': engine.last_update,
                'symbol': engine.symbol,
            }
        return None

    def get_recent_trades(
        self, trading_pair: TradingPairType, limit: int = 10
    ) -> list[TradeSettlement]:
        """获取最近的成交记录"""
        pair_symbol = trading_pair.value
        if pair_symbol in self.trading_pair_engines:
            return self.trading_pair_engines[pair_symbol].get_recent_trades(limit)
        return []

    def get_order(self, order_id: str) -> Order | None:
        """获取订单信息"""
        return self.orders.get(order_id)

    def get_order_status(self, order_id: str) -> dict:
        """获取订单详细状态"""
        order = self.orders.get(order_id)
        if not order:
            raise ValueError(f'不存在的订单: {order_id}')

        user = self.get_user(order.user_id)
        username = user.username if user else '未知用户'

        return {
            'order': order.model_dump(),
            'username': username,
            'trading_pair': order.trading_pair.value,
            'filled_percentage': (order.filled_base_amount / order.base_amount * 100)
            if order.base_amount is not None and order.base_amount > 0
            else 0,
            'is_active': order.status in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED],
        }

    # ====================
    # 内部实现 - 私有方法
    # ====================

    def _place_market_order(
        self,
        user: User,
        order_type: OrderType,
        trading_pair: TradingPairType,
        quote_amount: float | None = None,
        base_amount: float | None = None,
    ) -> Order:
        """处理市价订单

        Args:
            user: 用户对象
            order_type: 订单类型（市价买入或卖出）
            trading_pair: 交易对类型
            quote_amount: 要花费的计价资产金额（可选）
            base_amount: 要交易的基础资产数量（可选）
        """
        pair_symbol = trading_pair.value
        if pair_symbol not in self.trading_pair_engines:
            raise ValueError(f'不存在的交易对: {pair_symbol}')

        # 根据订单类型和指定参数确定实际交易数量
        current_price = self.get_market_price(trading_pair)

        if order_type == OrderType.MARKET_BUY:
            # 市价买入：可以指定quote_amount（花费金额）或base_amount（目标数量）
            if quote_amount is not None and quote_amount > 0:
                # 指定了花费金额，计算可获得的基础资产数量
                base_amount = quote_amount / current_price
                actual_quote_amount = quote_amount
            elif base_amount is not None and base_amount > 0:
                # 指定了目标数量，计算需要的花费金额
                actual_quote_amount = base_amount * current_price
            else:
                raise ValueError('市价买单必须指定基础资产数量或计价资产金额')

        else:  # MARKET_SELL
            # 市价卖出：可以指定base_amount（卖出数量）或quote_amount（目标获得金额）
            if base_amount is not None and base_amount > 0:
                # 指定了卖出数量
                actual_quote_amount = base_amount * current_price
            elif quote_amount is not None and quote_amount > 0:
                # 指定了目标获得金额，计算需要卖出的数量
                base_amount = quote_amount / current_price
                actual_quote_amount = quote_amount
            else:
                raise ValueError('市价卖单必须指定基础资产数量或计价资产金额')

        # 创建市价订单 - 只设置实际使用的字段
        if order_type == OrderType.MARKET_BUY:
            # 市价买单：如果指定了quote_amount，则设置quote_amount；否则设置base_amount
            if quote_amount is not None and quote_amount > 0:
                order = Order(
                    user=user,
                    order_type=order_type,
                    trading_pair=trading_pair,
                    base_amount=None,
                    price=None,  # 市价订单不指定价格
                    quote_amount=actual_quote_amount,
                )
            else:
                order = Order(
                    user=user,
                    order_type=order_type,
                    trading_pair=trading_pair,
                    base_amount=base_amount,
                    price=None,  # 市价订单不指定价格
                    quote_amount=None,
                )
        else:  # MARKET_SELL
            # 市价卖单：如果指定了quote_amount，则设置quote_amount；否则设置base_amount
            if quote_amount is not None and quote_amount > 0:
                order = Order(
                    user=user,
                    order_type=order_type,
                    trading_pair=trading_pair,
                    base_amount=None,
                    price=None,  # 市价订单不指定价格
                    quote_amount=actual_quote_amount,
                )
            else:
                order = Order(
                    user=user,
                    order_type=order_type,
                    trading_pair=trading_pair,
                    base_amount=base_amount,
                    price=None,  # 市价订单不指定价格
                    quote_amount=None,
                )

        # 冻结相应资产
        if order_type == OrderType.MARKET_BUY:
            # 市价买单：冻结实际需要的计价资产金额
            user.update_balance(
                asset=trading_pair.quote_asset,
                available_change=-actual_quote_amount,
                locked_change=actual_quote_amount,
            )
        else:  # MARKET_SELL
            # 市价卖单：冻结实际卖出的基础资产数量
            user.update_balance(
                asset=trading_pair.base_asset,
                available_change=-base_amount,
                locked_change=base_amount,
            )

        # 存储订单
        self.orders[order.id] = order

        # 使用交易对引擎处理市价订单
        trading_pair_engine = self.trading_pair_engines[pair_symbol]
        trading_pair_engine.add_order(order)

        # 执行订单匹配并处理交易
        trades = trading_pair_engine.match_orders()

        # 交易结算已移动到TradingPairEngine层面处理，仅收集交易记录
        self.trade_settlements.extend(trades)

        # 更新交易对价格
        for trade in trades:
            self._update_trading_pair_price(pair_symbol, trade.price)

        return order

    def _cancel_opposite_orders(
        self, user: User, trading_pair: TradingPairType, new_order_type: OrderType
    ) -> None:
        """撤销用户当前资产的相反方向订单"""
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
            for order in self.orders.values()
            if order.user.id == user.id
            and order.trading_pair == trading_pair
            and order.order_type in opposite_types
            and order.status in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]
        ]

        # 撤销这些订单
        for order in opposite_orders:
            try:
                self.cancel_order(user, order.id)
                logger.debug(
                    f'用户 {user.username} 撤销相反方向订单: {order.order_type.value} {order.base_amount} {trading_pair.value}'
                )
            except ValueError as e:
                logger.warning(f'撤销订单失败: {e}')

    def _get_recent_trades_for_trading_pair(
        self, trading_pair: TradingPairType, limit: int
    ) -> list[TradeSettlement]:
        """获取特定交易对的最近成交记录"""
        pair_symbol = trading_pair.value
        if pair_symbol in self.trading_pair_engines:
            return self.trading_pair_engines[pair_symbol].get_recent_trades(limit)
        return []

    def _update_trading_pair_price(self, pair_symbol: str, price: float) -> None:
        """更新交易对价格"""
        if pair_symbol in self.trading_pair_engines:
            old_price = self.trading_pair_engines[pair_symbol].current_price
            self.trading_pair_engines[pair_symbol].current_price = price
            self.trading_pair_engines[pair_symbol].last_update = datetime.now()

            if old_price != price:
                logger.debug(f'{pair_symbol} 价格更新: ${old_price:,.2f} -> ${price:,.2f}')
