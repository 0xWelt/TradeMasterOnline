"""模拟交易所核心逻辑。

该模块实现了完整的交易所功能，包括订单管理、交易撮合、资产管理和市场数据提供。
支持限价订单、市价订单，提供实时价格更新和用户余额管理。
"""

from __future__ import annotations

from loguru import logger

from .constants import AssetType, OrderType, TradingPairType
from .trading_pair import TradingPairEngine
from .typing import Asset, Order, Portfolio, User


class Exchange:
    """模拟交易所 - 提供用户管理和资产操作功能。

    交易所主要负责用户管理和资产操作，所有交易逻辑委托给TradingPairEngine处理。

    Attributes:
        assets: 支持的资产字典，包含所有可交易资产的详细信息。
        trading_pair_engines: 交易对引擎字典，每个交易对由独立的TradingPairEngine管理。
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

        # 用户管理
        self.users: dict[str, User] = {}

    # ====================
    # 用户管理
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
    # 交易
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
        """下单并立即执行匹配。

        委托给对应的TradingPairEngine处理所有订单逻辑。
        """
        # 验证用户合法性
        if user.id not in self.users or user != self.users[user.id]:
            raise ValueError('无效用户或用户对象不一致')

        # 验证交易对类型
        if trading_pair.value not in self.trading_pair_engines:
            raise ValueError(f'不支持的交易对: {trading_pair.value}')

        # 使用交易对引擎处理订单
        pair_symbol = trading_pair.value
        trading_pair_engine = self.trading_pair_engines[pair_symbol]

        # 委托给交易对引擎处理订单
        return trading_pair_engine.place_order(
            user=user,
            order_type=order_type,
            base_amount=base_amount,
            price=price,
            quote_amount=quote_amount,
        )

    def cancel_order(self, order: Order) -> bool:
        """取消订单。

        委托给对应的TradingPairEngine处理所有订单逻辑。
        """
        # 使用交易对引擎处理取消订单
        pair_symbol = order.trading_pair.value
        trading_pair_engine = self.trading_pair_engines[pair_symbol]
        return trading_pair_engine.cancel_order(order)
