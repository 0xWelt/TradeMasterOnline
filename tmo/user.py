"""用户管理模块。

该模块实现了用户模型和相关操作，包括资产管理和余额操作。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from .constants import AssetType, OrderType, TradingPairType


if TYPE_CHECKING:
    from .typing import Order


class User(BaseModel):
    """用户模型。

    表示交易所系统中的用户，包含用户基本信息和资产管理功能。
    用户直接存储总资产，通过动态计算获取可用余额和锁定余额。

    Attributes:
        id: 用户唯一标识符，由系统自动生成UUID。
        username: 用户名，具有唯一性。
        email: 用户邮箱地址，用于联系和验证。
        created_at: 用户创建时间，记录注册时间。
        total_assets: 用户总资产字典，键为资产类型，值为总资产数量。
        active_orders: 用户当前活跃挂单字典，按交易对和订单类型分类存储所有待成交订单。
        completed_orders: 用户已完成订单字典，按交易对分类存储已成交、已取消的订单。
    """

    model_config = {'extra': 'forbid'}

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), frozen=True)
    """用户唯一标识符，由系统自动生成UUID。"""

    username: str = Field(frozen=True)
    """用户名，具有唯一性。"""

    email: str = Field(frozen=True)
    """用户邮箱地址，用于联系和验证。"""

    created_at: datetime = Field(default_factory=datetime.now, frozen=True)
    """用户创建时间，记录注册时间。"""

    total_assets: dict[AssetType, float] = Field(default_factory=dict)
    """用户总资产字典，键为资产类型，值为总资产数量。"""

    active_orders: dict[TradingPairType, dict[OrderType, list['Order']]] = Field(
        default_factory=dict
    )
    """用户当前活跃挂单字典，按交易对和订单类型分类存储所有待成交订单。"""

    completed_orders: dict[TradingPairType, list['Order']] = Field(default_factory=dict)
    """用户已完成订单字典，按交易对分类存储已成交、已取消的订单。"""

    def add_active_order(self, order: Order) -> None:
        """添加活跃订单到用户订单管理。"""
        trading_pair = order.trading_pair
        order_type = order.order_type

        if trading_pair not in self.active_orders:
            self.active_orders[trading_pair] = {}
        if order_type not in self.active_orders[trading_pair]:
            self.active_orders[trading_pair][order_type] = []

        self.active_orders[trading_pair][order_type].append(order)

    def move_order_to_completed(self, order: Order) -> None:
        """将订单从活跃订单移动到已完成订单。"""
        trading_pair = order.trading_pair
        order_type = order.order_type

        # 从活跃订单中移除
        if (
            trading_pair in self.active_orders
            and order_type in self.active_orders[trading_pair]
            and order in self.active_orders[trading_pair][order_type]
        ):
            self.active_orders[trading_pair][order_type].remove(order)

        # 添加到已完成订单
        if trading_pair not in self.completed_orders:
            self.completed_orders[trading_pair] = []
        self.completed_orders[trading_pair].append(order)

    def get_active_orders(self, trading_pair: TradingPairType, order_type: OrderType) -> list:
        """获取用户特定交易对和订单类型的活跃订单。

        Args:
            trading_pair: 交易对类型。
            order_type: 订单类型。

        Returns:
            list: 用户的活跃订单列表。
        """
        if trading_pair not in self.active_orders:
            return []
        return self.active_orders[trading_pair].get(order_type, [])

    def get_all_active_orders(self, trading_pair: TradingPairType) -> dict[OrderType, list]:
        """获取用户特定交易对的所有活跃订单。

        Args:
            trading_pair: 交易对类型。

        Returns:
            dict: 按订单类型分类的活跃订单字典。
        """
        return self.active_orders.get(trading_pair, {})

    def get_completed_orders(self, trading_pair: TradingPairType) -> list:
        """获取用户特定交易对的已完成订单。

        Args:
            trading_pair: 交易对类型。

        Returns:
            list: 用户的已完成订单列表。
        """
        return self.completed_orders.get(trading_pair, [])

    def get_locked_balance(self, asset: AssetType) -> float:
        """获取用户指定资产的锁定余额。

        通过计算该资产关联的所有交易对中活跃订单的锁定资产之和得到。

        Args:
            asset: 要查询的资产类型。

        Returns:
            float: 用户在该资产上的锁定余额。
        """
        locked_total = 0.0

        # 获取与该资产相关的所有交易对
        related_pairs = asset.trading_pairs

        for pair in related_pairs:
            # 检查该交易对的活跃订单
            if pair in self.active_orders:
                # 检查买单（会锁定计价资产）
                if OrderType.BUY in self.active_orders[pair]:
                    for order in self.active_orders[pair][OrderType.BUY]:
                        if pair.quote_asset == asset:
                            if order.base_amount is not None and order.price is not None:
                                locked_total += order.base_amount * order.price
                            elif order.quote_amount is not None:
                                locked_total += order.quote_amount

                # 检查卖单（会锁定基础资产）
                if OrderType.SELL in self.active_orders[pair]:
                    for order in self.active_orders[pair][OrderType.SELL]:
                        if pair.base_asset == asset:
                            if order.base_amount is not None:
                                locked_total += order.base_amount
                            elif order.quote_amount is not None and order.price is not None:
                                locked_total += order.quote_amount / order.price

                # 检查市价买单
                if OrderType.MARKET_BUY in self.active_orders[pair]:
                    for order in self.active_orders[pair][OrderType.MARKET_BUY]:
                        if pair.quote_asset == asset and order.quote_amount is not None:
                            locked_total += order.quote_amount

                # 检查市价卖单
                if OrderType.MARKET_SELL in self.active_orders[pair]:
                    for order in self.active_orders[pair][OrderType.MARKET_SELL]:
                        if pair.base_asset == asset and order.base_amount is not None:
                            locked_total += order.base_amount

        return locked_total

    def get_available_balance(self, asset: AssetType) -> float:
        """获取用户指定资产的可用余额。

        通过总资产减去锁定余额计算得到。

        Args:
            asset: 要查询的资产类型。

        Returns:
            float: 用户在该资产上的可用余额。

        Example:
            >>> balance = user.get_available_balance(AssetType.BTC)
            >>> print(balance)
            1.5
        """
        total = self.total_assets.get(asset, 0.0)
        locked = self.get_locked_balance(asset)
        return max(0.0, total - locked)

    def get_total_balance(self, asset: AssetType) -> float:
        """获取用户指定资产的总余额。

        Args:
            asset: 要查询的资产类型。

        Returns:
            float: 用户在该资产上的总余额。

        Example:
            >>> balance = user.get_total_balance(AssetType.BTC)
            >>> print(balance)
            2.5
        """
        return self.total_assets.get(asset, 0.0)

    def deposit(self, asset: AssetType, amount: float) -> None:
        """用户充值。

        为用户指定资产增加总资产，模拟用户充值资产到交易所。

        Args:
            asset: 要充值的资产类型。
            amount: 充值金额，必须大于0。

        Raises:
            ValueError: 如果充值金额小于等于0。

        Example:
            >>> user.deposit(AssetType.USDT, 1000.0)
        """
        if amount <= 0:
            raise ValueError('充值金额必须大于0')

        self.total_assets[asset] = self.total_assets.get(asset, 0.0) + amount

    def withdraw(self, asset: AssetType, amount: float) -> None:
        """用户提现。

        从用户指定资产的可用余额中扣除相应金额，模拟用户从交易所提现。

        Args:
            asset: 要提现的资产类型。
            amount: 提现金额，必须大于0。

        Raises:
            ValueError: 如果提现金额小于等于0，或用户可用余额不足。

        Example:
            >>> user.withdraw(AssetType.USDT, 500.0)
        """
        if amount <= 0:
            raise ValueError('提现金额必须大于0')

        available = self.get_available_balance(asset)
        if available < amount:
            raise ValueError('可用余额不足')

        # 直接减少总资产
        self.total_assets[asset] = self.total_assets.get(asset, 0.0) - amount

    def update_total_asset(self, asset: AssetType, change: float) -> None:
        """更新用户总资产。

        用于交易结算时更新用户的总资产。

        Args:
            asset: 要更新的资产类型。
            change: 资产变化量，正值表示增加，负值表示减少。

        Example:
            >>> user.update_total_asset(AssetType.BTC, 1.5)
        """
        self.total_assets[asset] = self.total_assets.get(asset, 0.0) + change

    @field_validator('id', 'created_at', mode='before')
    @classmethod
    def _validate_auto_generated_fields(cls, v: object, info: ValidationInfo) -> object:
        """验证自动生成的字段。

        对于系统自动生成的字段（id和created_at），忽略用户提供的值，
        始终使用系统默认值。

        Args:
            v: 字段值，如果为None则使用默认值。
            info: 验证信息，包含字段名等上下文。

        Returns:
            object: 处理后的字段值。
        """
        if v is not None:
            # 忽略用户提供的值，使用默认值
            if info.field_name == 'id':
                return str(uuid.uuid4())
            elif info.field_name == 'created_at':
                return datetime.now()
        return v

    def __init__(self, **data):
        """初始化用户模型。

        确保所有必要的字段都被正确初始化，并为所有资产类型创建0初始余额。
        """
        super().__init__(**data)
        # 为所有资产类型创建0初始余额
        for asset_type in AssetType:
            if asset_type not in self.total_assets:
                self.total_assets[asset_type] = 0.0
