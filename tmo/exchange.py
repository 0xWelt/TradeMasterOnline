"""模拟交易所核心逻辑。

该模块实现了完整的交易所功能，包括订单管理、交易撮合、资产管理和市场数据提供。
支持限价订单、市价订单，提供实时价格更新和用户余额管理。
"""

from __future__ import annotations

from loguru import logger

from .constants import TradingPairType
from .trading_pair import TradingPairEngine
from .user import User


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
        - 初始化交易对和初始价格
        - 设置空的订单簿和交易记录
        - 初始化用户管理
        """
        # 用户管理
        self.users: dict[str, User] = {}

        # 交易对引擎 - 使用新的TradingPair类管理每个交易对
        self.trading_pair_engines: dict[TradingPairType, TradingPairEngine] = {
            pair: TradingPairEngine(trading_pair_type=pair, users=self.users)
            for pair in TradingPairType
        }

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
        self.users[user.id] = user
        logger.debug(f'创建用户: {username} ({email})')
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

    # ====================
    # 交易
    # ====================

    def get_trading_pair(self, trading_pair: TradingPairType) -> TradingPairEngine:
        """获取指定交易对的交易引擎。

        Args:
            trading_pair: 交易对类型枚举。

        Returns:
            TradingPairEngine: 对应的交易对引擎。

        Raises:
            ValueError: 如果交易对不支持。

        Example:
            >>> exchange = Exchange()
            >>> trading_pair = exchange.get_trading_pair(TradingPairType.BTC_USDT)
            >>> order = trading_pair.place_order(user, OrderType.BUY, base_amount=1.0, price=50000.0)
        """
        if trading_pair not in self.trading_pair_engines:
            raise ValueError(f'不支持的交易对: {trading_pair}')

        return self.trading_pair_engines[trading_pair]
