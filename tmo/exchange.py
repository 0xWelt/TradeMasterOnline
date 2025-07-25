"""模拟交易所核心逻辑"""

from __future__ import annotations

from datetime import datetime

from loguru import logger

from .constants import AssetType, OrderType, TradingPairType
from .typing import Asset, Order, Portfolio, Trade, TradingPair, User


class Exchange:
    """模拟交易所 - 提供完整的交易撮合系统"""

    def __init__(self):
        """初始化交易所"""
        # 支持的资产
        self.assets: dict[AssetType, Asset] = {
            AssetType.USDT: Asset(
                symbol=AssetType.USDT, name='Tether USD', description='美元稳定币'
            ),
            AssetType.BTC: Asset(symbol=AssetType.BTC, name='Bitcoin', description='比特币'),
            AssetType.ETH: Asset(symbol=AssetType.ETH, name='Ethereum', description='以太坊'),
        }

        # 交易对 - 使用TradingPairType枚举自动生成价格
        self.trading_pairs: dict[str, TradingPair] = {
            pair.value: TradingPair(
                base_asset=pair.base_asset,
                quote_asset=pair.quote_asset,
                current_price=pair.initial_price,
            )
            for pair in TradingPairType
        }

        # 订单簿：按价格排序的订单列表
        self.order_books: dict[str, dict[OrderType, list[Order]]] = {
            pair.value: {
                OrderType.BUY: [],  # 买单按价格降序排列
                OrderType.SELL: [],  # 卖单按价格升序排列
                OrderType.MARKET_BUY: [],  # 市价买单
                OrderType.MARKET_SELL: [],  # 市价卖单
            }
            for pair in TradingPairType
        }

        # 成交记录
        self.trades: list[Trade] = []

        # 订单索引
        self.orders: dict[str, Order] = {}

        # 用户管理
        self.users: dict[str, User] = {}

    # ====================
    # 用户管理 - 新增功能
    # ====================

    def create_user(self, username: str, email: str) -> User:
        """创建新用户"""
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
                total_balance=1000.0 if asset_type == AssetType.USDT else 0.0,
            )

        self.users[user.id] = user
        logger.debug(f'创建用户: {username} ({email}) - 初始USDT余额: 1000.0')
        return user

    def get_user(self, user_id: str) -> User | None:
        """获取用户信息"""
        return self.users.get(user_id)

    def list_users(self) -> list[User]:
        """获取所有用户列表"""
        return list(self.users.values())

    def get_user_portfolio(self, user: User, asset: AssetType) -> Portfolio:
        """获取用户特定资产的持仓"""
        return user.portfolios[asset]

    def get_user_portfolios(self, user: User) -> dict[AssetType, Portfolio]:
        """获取用户所有持仓"""
        return user.portfolios

    # ====================
    # 资产操作 - 新增功能
    # ====================

    def deposit(self, user: User, asset: AssetType, amount: float) -> None:
        """用户充值"""
        if amount <= 0:
            raise ValueError('充值金额必须大于0')

        portfolio = user.portfolios[asset]
        portfolio.available_balance += amount
        portfolio.total_balance += amount

        logger.debug(f'用户 {user.username} 充值 {amount} {asset.value}')

    def withdraw(self, user: User, asset: AssetType, amount: float) -> None:
        """用户提现"""
        if amount <= 0:
            raise ValueError('提现金额必须大于0')

        portfolio = user.portfolios[asset]
        if portfolio.available_balance < amount:
            raise ValueError('可用余额不足')

        portfolio.available_balance -= amount
        portfolio.total_balance -= amount

        logger.debug(f'用户 {user.username} 提现 {amount} {asset.value}')

    # ====================
    # 操作接口 - 订单管理
    # ====================

    def place_order(
        self,
        user: User,
        order_type: OrderType,
        asset: AssetType,
        quantity: float = 0.0,
        price: float = 0.0,
        amount: float = 0.0,
    ) -> Order:
        """下单并立即执行匹配"""
        # 验证用户合法性
        if user.id not in self.users or user != self.users[user.id]:
            raise ValueError('无效用户或用户对象不一致')

        # 验证资产类型
        if asset not in self.assets:
            raise ValueError(f'不支持的资产类型: {asset}')

        # 处理单边持仓逻辑：撤销相反方向的订单
        self._cancel_opposite_orders(user, asset, order_type)

        # 根据订单类型处理参数
        quantity, price, amount = self._process_order_parameters(
            order_type, asset, quantity, price, amount
        )

        # 验证用户持仓
        self._validate_order_balance(user, order_type, asset, quantity, price, amount)

        # 处理市价订单
        if order_type in [OrderType.MARKET_BUY, OrderType.MARKET_SELL]:
            return self._place_market_order(user, order_type, asset, amount)

        order = Order(
            user=user,
            order_type=order_type,
            asset=asset,
            quantity=quantity,
            price=price,
            amount=amount,
        )

        logger.debug(
            f'用户 {user.username} 下 {order_type.value} 单: {quantity} {asset.value} @ ${price:,.2f}'
        )

        # 冻结相应资产
        if order_type == OrderType.BUY:
            # 买单锁定USDT
            required_usdt = quantity * price
            user.update_balance(
                asset=AssetType.USDT, available_change=-required_usdt, locked_change=required_usdt
            )
        else:
            # 卖单锁定BTC
            user.update_balance(asset=asset, available_change=-quantity, locked_change=quantity)

        # 存储订单
        self.orders[order.id] = order

        # 只将限价订单添加到订单簿，市价订单立即执行
        if order.order_type in [OrderType.BUY, OrderType.SELL]:
            self._process_new_order(order)

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

        # 从订单簿中移除
        self._remove_from_order_book(order)

        # 释放冻结的资产
        order.on_cancelled()

        # 更新订单状态
        order.status = 'cancelled'
        logger.debug(
            f'用户 {user.username} 取消订单: {order.quantity} {order.asset.value} @ ${order.price:,.2f}'
        )

        return True

    def get_user_orders(self, user: User) -> list[Order]:
        """获取用户的所有订单"""
        return [order for order in self.orders.values() if order.user.id == user.id]

    def get_user_trades(self, user: User) -> list[Trade]:
        """获取用户的所有成交记录"""
        user_orders = {order.id for order in self.get_user_orders(user)}
        return [
            trade
            for trade in self.trades
            if trade.buy_order_id in user_orders or trade.sell_order_id in user_orders
        ]

    # ====================
    # 内部持仓管理方法
    # ====================

    def _process_order_parameters(
        self, order_type: OrderType, asset: AssetType, quantity: float, price: float, amount: float
    ) -> tuple[float, float, float]:
        """处理订单参数，根据订单类型返回合适的数量和价格

        Args:
            order_type: 订单类型
            asset: 资产类型
            quantity: 数量（对应目标货币，可能为0）
            price: 价格（限价订单使用，可能为0）
            amount: 金额（对应计价货币，可能为0）

        Returns:
            tuple: (处理后的数量, 处理后的价格, 处理后的金额)
        """
        # 处理市价订单：只能指定金额，不能设定价格和数量
        if order_type in [OrderType.MARKET_BUY, OrderType.MARKET_SELL]:
            if amount <= 0:
                raise ValueError('市价订单必须指定金额（计价货币）')
            if quantity > 0:
                raise ValueError('市价订单不能指定数量')
            if price > 0:
                raise ValueError('市价订单不能指定价格')

            # 对于市价订单，数量和价格会在执行时确定
            return 0.0, 0.0, amount

        # 处理限价订单：可以指定数量或金额，自动计算另一个
        if order_type in [OrderType.BUY, OrderType.SELL]:
            # 必须指定价格
            if price <= 0:
                raise ValueError('限价订单价格必须大于0')

            # 必须指定数量或金额中的至少一个，但不能同时指定
            if quantity > 0 and amount > 0:
                raise ValueError('限价订单只能指定数量或金额，不能同时指定')
            if quantity <= 0 and amount <= 0:
                raise ValueError('限价订单必须指定数量或金额')

            # 如果只指定了金额，计算对应数量
            if amount > 0 and quantity <= 0:
                quantity = amount / price

            # 如果只指定了数量，计算对应金额
            if quantity > 0 and amount <= 0:
                amount = quantity * price

            return quantity, price, amount

        raise ValueError(f'不支持的订单类型: {order_type}')

    def _validate_order_balance(
        self,
        user: User,
        order_type: OrderType,
        asset: AssetType,
        quantity: float,
        price: float = 0.0,
        amount: float = 0.0,
    ) -> None:
        """验证订单余额"""
        if order_type in [OrderType.BUY, OrderType.MARKET_BUY]:
            # 对于市价买单，直接使用指定的金额
            if order_type == OrderType.MARKET_BUY:
                required_usdt = amount
            else:
                # 对于限价买单，使用计算后的金额
                required_usdt = quantity * price

            usdt_portfolio = user.portfolios[AssetType.USDT]
            if usdt_portfolio.available_balance < required_usdt:
                raise ValueError(
                    f'USDT余额不足，需要 {required_usdt:.2f} USDT，可用 {usdt_portfolio.available_balance:.2f} USDT'
                )
        else:  # SELL or MARKET_SELL
            if order_type == OrderType.MARKET_SELL:
                # 对于市价卖单，需要先计算数量（基于金额和当前价格）
                current_price = self.get_market_price(asset)
                required_asset_quantity = amount / current_price
            else:
                # 对于限价卖单，使用指定的数量
                required_asset_quantity = quantity

            asset_portfolio = user.portfolios[asset]
            if asset_portfolio.available_balance < required_asset_quantity:
                raise ValueError(
                    f'{asset.value}余额不足，需要 {required_asset_quantity} {asset.value}，可用 {asset_portfolio.available_balance} {asset.value}'
                )

    def _lock_balance_for_order(
        self,
        user: User,
        order_type: OrderType,
        asset: AssetType,
        quantity: float,
        price: float,
        amount: float,
    ) -> None:
        """为订单锁定余额"""
        if order_type in [OrderType.BUY, OrderType.MARKET_BUY]:
            # 买单锁定USDT
            if order_type == OrderType.MARKET_BUY:
                # 市价买单直接锁定指定金额
                required_usdt = amount
            else:
                # 限价买单使用计算后的金额
                required_usdt = quantity * price
            usdt_portfolio = user.portfolios[AssetType.USDT]
            usdt_portfolio.available_balance -= required_usdt
            usdt_portfolio.locked_balance += required_usdt
        else:  # SELL or MARKET_SELL
            if order_type == OrderType.MARKET_SELL:
                # 市价卖单：根据金额计算需要锁定的资产数量
                current_price = self.get_market_price(asset)
                required_asset_quantity = amount / current_price
            else:
                # 限价卖单：直接锁定指定数量
                required_asset_quantity = quantity

            # 卖单锁定资产
            asset_portfolio = user.portfolios[asset]
            asset_portfolio.available_balance -= required_asset_quantity
            asset_portfolio.locked_balance += required_asset_quantity

    def _unlock_balance_for_order(self, user: User, order: Order) -> None:
        """释放订单锁定的余额"""
        if order.order_type == OrderType.BUY:
            # 释放锁定的USDT
            locked_usdt = order.remaining_quantity * order.price
            usdt_portfolio = user.portfolios[AssetType.USDT]
            usdt_portfolio.locked_balance -= locked_usdt
            usdt_portfolio.available_balance += locked_usdt
        else:
            # 释放锁定的BTC
            locked_btc = order.remaining_quantity
            btc_portfolio = user.portfolios[order.asset]
            btc_portfolio.locked_balance -= locked_btc
            btc_portfolio.available_balance += locked_btc

    def _update_balances_after_trade(self, buyer: User, seller: User, trade: Trade) -> None:
        """交易完成后更新余额"""
        trade_amount = trade.quantity * trade.price

        # 买家获得BTC，减少USDT
        buyer_btc = buyer.portfolios[trade.asset]

        buyer_btc.available_balance += trade.quantity
        buyer_btc.total_balance += trade.quantity

        # 卖家获得USDT，减少BTC
        seller_btc = seller.portfolios[trade.asset]
        seller_usdt = seller.portfolios[AssetType.USDT]

        seller_usdt.available_balance += trade_amount
        seller_usdt.total_balance += trade_amount
        seller_btc.locked_balance -= trade.quantity
        seller_btc.total_balance -= trade.quantity

    # ====================
    # 状态快照接口
    # ====================

    def get_state_snapshot(self) -> dict:
        """获取交易所完整状态快照"""
        return {
            'assets': self.assets.copy(),
            'trading_pairs': {
                symbol: {
                    'base_asset': pair.base_asset,
                    'quote_asset': pair.quote_asset,
                    'current_price': pair.current_price,
                    'last_update': pair.last_update,
                }
                for symbol, pair in self.trading_pairs.items()
            },
            'order_books': {
                symbol: {
                    'BUY': [order.model_dump() for order in orders[OrderType.BUY]],
                    'SELL': [order.model_dump() for order in orders[OrderType.SELL]],
                }
                for symbol, orders in self.order_books.items()
            },
            'trades': [trade.model_dump() for trade in self.trades],
            'orders': {order_id: order.model_dump() for order_id, order in self.orders.items()},
            'users': {user_id: user.model_dump() for user_id, user in self.users.items()},
        }

    # ====================
    # 查询接口
    # ====================

    def get_market_price(self, asset: AssetType) -> float:
        """获取交易对当前市场价格"""
        pair_symbol = f'{asset.value}/USDT'
        if pair_symbol in self.trading_pairs:
            return self.trading_pairs[pair_symbol].current_price
        raise ValueError(f'不存在的交易对: {pair_symbol}')

    def get_market_depth(self, asset: AssetType) -> dict:
        """获取交易对市场深度信息"""
        pair_symbol = f'{asset.value}/USDT'
        if pair_symbol not in self.order_books:
            return {'bids': [], 'asks': []}

        order_book = self.order_books[pair_symbol]
        return {
            'bids': [
                {'price': order.price, 'quantity': order.remaining_quantity}
                for order in order_book[OrderType.BUY]
            ],
            'asks': [
                {'price': order.price, 'quantity': order.remaining_quantity}
                for order in order_book[OrderType.SELL]
            ],
        }

    def get_market_summary(self, asset: AssetType) -> dict:
        """获取交易对市场摘要"""
        pair_symbol = f'{asset.value}/USDT'
        if pair_symbol not in self.trading_pairs:
            raise ValueError(f'不存在的交易对: {pair_symbol}')

        trading_pair = self.trading_pairs[pair_symbol]
        recent_trades = self._get_recent_trades_for_asset(asset, limit=50)
        order_book = self.order_books[pair_symbol]

        return {
            'symbol': pair_symbol,
            'current_price': trading_pair.current_price,
            'last_update': trading_pair.last_update,
            'total_bids': len(order_book[OrderType.BUY]),
            'total_asks': len(order_book[OrderType.SELL]),
            'recent_trades': len(recent_trades),
            'best_bid': order_book[OrderType.BUY][0].price if order_book[OrderType.BUY] else None,
            'best_ask': order_book[OrderType.SELL][0].price if order_book[OrderType.SELL] else None,
        }

    def get_order_book(self, asset: AssetType) -> dict[OrderType, list[Order]]:
        """获取订单簿"""
        pair_symbol = f'{asset.value}/USDT'
        if pair_symbol in self.order_books:
            return self.order_books[pair_symbol].copy()
        return {OrderType.BUY: [], OrderType.SELL: []}

    def get_trading_pair(self, asset: AssetType) -> TradingPair | None:
        """获取交易对信息"""
        pair_symbol = f'{asset.value}/USDT'
        return self.trading_pairs.get(pair_symbol)

    def get_recent_trades(self, asset: AssetType, limit: int = 10) -> list[Trade]:
        """获取最近的成交记录"""
        return self._get_recent_trades_for_asset(asset, limit)

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
            'trading_pair': f'{order.asset.value}/USDT',
            'filled_percentage': (order.filled_quantity / order.quantity * 100)
            if order.quantity > 0
            else 0,
            'is_active': order.status in ['pending', 'partially_filled'],
        }

    # ====================
    # 内部实现 - 私有方法
    # ====================

    def _place_market_order(
        self, user: User, order_type: OrderType, asset: AssetType, amount: float
    ) -> Order:
        """处理市价订单

        Args:
            user: 用户对象
            order_type: 订单类型（市价买入或卖出）
            asset: 资产类型
            amount: 计价货币金额（USDT），用于市价买入时表示要花费的USDT金额，
                   用于市价卖出时表示要获得的USDT金额（通过卖出资产获得）
        """
        pair_symbol = f'{asset.value}/USDT'
        if pair_symbol not in self.order_books:
            raise ValueError(f'不存在的交易对: {pair_symbol}')

        # 根据订单类型计算交易数量
        current_price = self.get_market_price(asset)
        if order_type == OrderType.MARKET_BUY:
            # 市价买入：使用金额计算可购买的资产数量
            quantity = amount / current_price
        else:  # MARKET_SELL
            # 市价卖出：使用金额计算需要卖出的资产数量
            quantity = amount / current_price

        # 创建市价订单
        order = Order(
            user=user,
            order_type=order_type,
            asset=asset,
            quantity=quantity,
            price=0.0,  # 市价订单价格为0
            amount=amount,  # 存储原始金额
        )

        # 冻结相应资产
        if order_type == OrderType.MARKET_BUY:
            # 市价买单：冻结指定的USDT金额
            user.update_balance(
                asset=AssetType.USDT, available_change=-amount, locked_change=amount
            )
        else:  # MARKET_SELL
            # 市价卖单：根据计算出的数量冻结相应资产
            user.update_balance(asset=asset, available_change=-quantity, locked_change=quantity)

        # 存储订单
        self.orders[order.id] = order

        # 立即执行市价订单匹配
        self._execute_market_order(order)

        return order

    def _get_max_possible_buy_price(self, asset: AssetType) -> float:
        """获取市价买单的最大可能价格"""
        pair_symbol = f'{asset.value}/USDT'
        if pair_symbol not in self.order_books:
            return self.trading_pairs[pair_symbol].current_price

        sell_orders = self.order_books[pair_symbol][OrderType.SELL]
        if sell_orders:
            return sell_orders[-1].price * 1.1  # 使用最高卖价的110%作为上限
        return self.trading_pairs[pair_symbol].current_price * 1.1

    def _cancel_opposite_orders(
        self, user: User, asset: AssetType, new_order_type: OrderType
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
            and order.asset == asset
            and order.order_type in opposite_types
            and order.status in ['pending', 'partially_filled']
        ]

        # 撤销这些订单
        for order in opposite_orders:
            try:
                self.cancel_order(user, order.id)
                logger.debug(
                    f'用户 {user.username} 撤销相反方向订单: {order.order_type.value} {order.quantity} {asset.value}'
                )
            except ValueError as e:
                logger.warning(f'撤销订单失败: {e}')

    def _execute_market_order(self, order: Order) -> None:
        """执行市价订单"""
        pair_symbol = f'{order.asset.value}/USDT'
        if pair_symbol not in self.order_books:
            return

        remaining_quantity = order.quantity
        total_cost = 0.0
        trades_executed = []

        if order.order_type == OrderType.MARKET_BUY:
            # 市价买单：从卖单簿中按价格从低到高成交
            sell_orders = self.order_books[pair_symbol][OrderType.SELL]
            for sell_order in sell_orders[:]:
                if remaining_quantity <= 0:
                    break

                available_quantity = sell_order.remaining_quantity
                trade_quantity = min(remaining_quantity, available_quantity)
                trade_price = sell_order.price

                # 执行交易
                trade = self._execute_trade_for_market_order(
                    order, sell_order, trade_quantity, trade_price
                )
                trades_executed.append(trade)
                total_cost += trade_quantity * trade_price
                remaining_quantity -= trade_quantity

        elif order.order_type == OrderType.MARKET_SELL:
            # 市价卖单：从买单簿中按价格从高到低成交
            buy_orders = self.order_books[pair_symbol][OrderType.BUY]
            for buy_order in buy_orders[:]:
                if remaining_quantity <= 0:
                    break

                available_quantity = buy_order.remaining_quantity
                trade_quantity = min(remaining_quantity, available_quantity)
                trade_price = buy_order.price

                # 执行交易
                trade = self._execute_trade_for_market_order(
                    buy_order, order, trade_quantity, trade_price
                )
                trades_executed.append(trade)
                total_cost += trade_quantity * trade_price
                remaining_quantity -= trade_quantity

        # 更新市价订单状态
        order.filled_quantity = order.quantity - remaining_quantity
        if remaining_quantity > 0:
            order.status = 'partially_filled'
        else:
            order.status = 'filled'

        # 释放多余的冻结资金
        if order.order_type == OrderType.MARKET_BUY:
            actual_required = total_cost
            original_amount = order.amount
            if original_amount > 0:
                excess = original_amount - actual_required
                if excess > 0:
                    user = order.user
                    user.update_balance(
                        asset=AssetType.USDT, available_change=excess, locked_change=-excess
                    )

        logger.debug(
            f'市价订单执行: {order.order_type.value} {order.filled_quantity}/{order.quantity} {order.asset.value}'
        )

    def _execute_trade_for_market_order(
        self, buy_order: Order, sell_order: Order, quantity: float, price: float
    ) -> Trade:
        """为市价订单执行交易"""
        # 更新订单成交数量
        buy_order.filled_quantity += quantity
        sell_order.filled_quantity += quantity

        # 创建成交记录
        trade = Trade(
            buy_order=buy_order,
            sell_order=sell_order,
            asset=buy_order.asset,
            quantity=quantity,
            price=price,
        )

        self.trades.append(trade)

        # 更新订单状态
        self._update_order_status(buy_order)
        self._update_order_status(sell_order)

        # 更新交易对价格
        pair_symbol = f'{buy_order.asset.value}/USDT'
        self._update_trading_pair_price(pair_symbol, price)

        # 更新用户持仓
        buyer = self.get_user(buy_order.user_id)
        seller = self.get_user(sell_order.user_id)
        if buyer and seller:
            self._update_balances_after_trade(buyer, seller, trade)

        # 清理已完成的订单
        self._cleanup_filled_orders(pair_symbol)

        return trade

    def _process_new_order(self, order: Order) -> None:
        """处理新订单：添加到订单簿并执行匹配"""
        pair_symbol = f'{order.asset.value}/USDT'
        if pair_symbol not in self.order_books:
            return

        # 添加到订单簿
        self._add_to_order_book(order)

        # 立即执行匹配
        self._match_orders(pair_symbol)

    def _add_to_order_book(self, order: Order) -> None:
        """将订单添加到订单簿"""
        pair_symbol = f'{order.asset.value}/USDT'
        order_list = self.order_books[pair_symbol][order.order_type]

        if order.order_type == OrderType.BUY:
            # 买单按价格降序排列（价格高的优先）
            self._insert_buy_order(order_list, order)
        else:
            # 卖单按价格升序排列（价格低的优先）
            self._insert_sell_order(order_list, order)

    def _insert_buy_order(self, order_list: list[Order], order: Order) -> None:
        """插入买单（价格降序）"""
        for i, existing_order in enumerate(order_list):
            if order.price > existing_order.price:
                order_list.insert(i, order)
                return
        order_list.append(order)

    def _insert_sell_order(self, order_list: list[Order], order: Order) -> None:
        """插入卖单（价格升序）"""
        for i, existing_order in enumerate(order_list):
            if order.price < existing_order.price:
                order_list.insert(i, order)
                return
        order_list.append(order)

    def _remove_from_order_book(self, order: Order) -> None:
        """从订单簿中移除订单"""
        pair_symbol = f'{order.asset.value}/USDT'
        if pair_symbol in self.order_books:
            order_list = self.order_books[pair_symbol][order.order_type]
            if order in order_list:
                order_list.remove(order)

    def _match_orders(self, pair_symbol: str) -> None:
        """匹配订单"""
        if pair_symbol not in self.order_books:
            return

        buy_orders = self.order_books[pair_symbol][OrderType.BUY]
        sell_orders = self.order_books[pair_symbol][OrderType.SELL]

        while buy_orders and sell_orders:
            buy_order = buy_orders[0]
            sell_order = sell_orders[0]

            # 检查是否可以成交
            if buy_order.price >= sell_order.price:
                # 可以成交
                trade = self._execute_trade(buy_order, sell_order)
                self.trades.append(trade)

                # 更新订单状态
                self._update_order_status(buy_order)
                self._update_order_status(sell_order)

                # 更新交易对价格
                self._update_trading_pair_price(pair_symbol, trade.price)

                # 更新用户持仓
                buyer = self.get_user(buy_order.user_id)
                seller = self.get_user(sell_order.user_id)
                if buyer and seller:
                    self._update_balances_after_trade(buyer, seller, trade)

                # 清理已完成的订单
                self._cleanup_filled_orders(pair_symbol)
            else:
                # 无法成交，退出循环
                break

    def _execute_trade(self, buy_order: Order, sell_order: Order) -> Trade:
        """执行交易"""
        # 确定成交数量和价格
        trade_quantity = min(buy_order.remaining_quantity, sell_order.remaining_quantity)
        trade_price = sell_order.price  # 按卖单价格成交

        # 更新订单已成交数量
        buy_order.filled_quantity += trade_quantity
        sell_order.filled_quantity += trade_quantity

        # 创建成交记录
        trade = Trade(
            buy_order=buy_order,
            sell_order=sell_order,
            asset=buy_order.asset,
            quantity=trade_quantity,
            price=trade_price,
        )

        # 获取用户信息用于日志
        buyer = buy_order.user
        seller = sell_order.user
        buyer_name = buyer.username if buyer else '未知买家'
        seller_name = seller.username if seller else '未知卖家'

        logger.debug(
            f'成交: {buyer_name} 从 {seller_name} 买入 {trade_quantity} '
            f'{buy_order.asset.value} @ ${trade_price:,.2f}'
        )
        return trade

    def _update_order_status(self, order: Order) -> None:
        """更新订单状态"""
        if order.is_filled:
            order.status = 'filled'
        elif order.is_partially_filled:
            order.status = 'partially_filled'

    def _update_trading_pair_price(self, pair_symbol: str, price: float) -> None:
        """更新交易对价格"""
        if pair_symbol in self.trading_pairs:
            old_price = self.trading_pairs[pair_symbol].current_price
            self.trading_pairs[pair_symbol].current_price = price
            self.trading_pairs[pair_symbol].last_update = datetime.now()

            if old_price != price:
                logger.debug(f'{pair_symbol} 价格更新: ${old_price:,.2f} -> ${price:,.2f}')

    def _cleanup_filled_orders(self, pair_symbol: str) -> None:
        """清理已完成的订单"""
        for order_type in [
            OrderType.BUY,
            OrderType.SELL,
            OrderType.MARKET_BUY,
            OrderType.MARKET_SELL,
        ]:
            if order_type in self.order_books[pair_symbol]:
                order_list = self.order_books[pair_symbol][order_type]
                # 移除已完成的订单
                order_list[:] = [order for order in order_list if not order.is_filled]

    def _get_recent_trades_for_asset(self, asset: AssetType, limit: int) -> list[Trade]:
        """获取特定资产的最近成交记录"""
        asset_trades = [trade for trade in self.trades if trade.asset == asset]
        return sorted(asset_trades, key=lambda x: x.timestamp, reverse=True)[:limit]
