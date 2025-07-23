"""交易所核心数据模型"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class AssetType(StrEnum):
    """资产类型"""

    USDT = 'USDT'
    BTC = 'BTC'


class OrderType(StrEnum):
    """订单类型"""

    BUY = 'buy'
    SELL = 'sell'


class Asset(BaseModel):
    """资产模型"""

    symbol: AssetType
    name: str
    description: str = ''


class Portfolio(BaseModel):
    """用户持仓模型"""

    asset: AssetType
    """资产类型"""
    available_balance: float = Field(default=0, ge=0)
    """可用余额"""
    locked_balance: float = Field(default=0, ge=0)
    """锁定余额"""
    total_balance: float = Field(default=0, ge=0)
    """总余额"""

    @property
    def is_zero(self) -> bool:
        """是否为零持仓"""
        return self.total_balance == 0


class User(BaseModel):
    """用户模型"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    """用户唯一标识"""
    username: str
    """用户名"""
    email: str
    """邮箱"""
    created_at: datetime = Field(default_factory=datetime.now)
    """创建时间"""
    portfolios: dict[AssetType, Portfolio] = Field(default_factory=dict)
    """持仓信息"""

    def update_balance(
        self, asset: AssetType, available_change: float, locked_change: float
    ) -> None:
        """更新用户余额

        Args:
            asset: 资产类型
            available_change: 可用余额变化量
            locked_change: 锁定余额变化量
        """
        if asset not in self.portfolios:
            self.portfolios[asset] = Portfolio(
                asset=asset,
                available_balance=0.0,
                locked_balance=0.0,
                total_balance=0.0,
            )

        portfolio = self.portfolios[asset]
        portfolio.available_balance += available_change
        portfolio.locked_balance += locked_change
        portfolio.total_balance = portfolio.available_balance + portfolio.locked_balance


class Order(BaseModel):
    """订单模型"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    """订单唯一标识"""
    user: User
    """关联的用户对象"""
    order_type: OrderType
    """订单类型：买入或卖出"""
    asset: AssetType
    """交易资产"""
    quantity: float = Field(gt=0)
    """数量"""
    price: float = Field(gt=0)
    """价格"""
    timestamp: datetime = Field(default_factory=datetime.now)
    """创建时间"""
    filled_quantity: float = Field(default=0, ge=0)
    """已成交数量"""
    status: str = Field(default='pending')
    """订单状态"""

    @property
    def user_id(self) -> str:
        """获取用户ID（兼容性属性）"""
        return self.user.id

    @property
    def remaining_quantity(self) -> float:
        """剩余未成交数量"""
        return self.quantity - self.filled_quantity

    @property
    def is_filled(self) -> bool:
        """是否完全成交"""
        return self.filled_quantity >= self.quantity

    @property
    def is_partially_filled(self) -> bool:
        """是否部分成交"""
        return 0 < self.filled_quantity < self.quantity

    def on_filled(self, trade: Trade) -> None:
        """订单成交时的回调"""
        if self.user is None:
            return

        if self.order_type == OrderType.BUY:
            # 买单：获得资产，减少计价资产
            self.user.update_balance(
                asset=self.asset, available_change=trade.quantity, locked_change=-trade.quantity
            )
            self.user.update_balance(
                asset=AssetType.USDT,
                available_change=-trade.quantity * trade.price,
                locked_change=0,
            )
        else:
            # 卖单：获得计价资产，减少资产
            self.user.update_balance(
                asset=AssetType.USDT, available_change=trade.quantity * trade.price, locked_change=0
            )
            self.user.update_balance(
                asset=self.asset, available_change=0, locked_change=-trade.quantity
            )

    def on_cancelled(self) -> None:
        """订单取消时的回调"""
        if self.user is None:
            return

        if self.order_type == OrderType.BUY:
            # 释放锁定的计价资产
            locked_amount = self.remaining_quantity * self.price
            self.user.update_balance(
                asset=AssetType.USDT, available_change=locked_amount, locked_change=-locked_amount
            )
        else:
            # 释放锁定的资产
            self.user.update_balance(
                asset=self.asset,
                available_change=self.remaining_quantity,
                locked_change=-self.remaining_quantity,
            )


class Trade(BaseModel):
    """成交记录模型"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    """成交记录唯一标识"""
    buy_order: Order
    """买单对象"""
    sell_order: Order
    """卖单对象"""
    asset: AssetType
    """交易资产"""
    quantity: float = Field(gt=0)
    """成交数量"""
    price: float = Field(gt=0)
    """成交价格"""
    timestamp: datetime = Field(default_factory=datetime.now)
    """成交时间"""

    @property
    def buy_order_id(self) -> str:
        """获取买单ID（兼容性属性）"""
        return self.buy_order.id

    @property
    def sell_order_id(self) -> str:
        """获取卖单ID（兼容性属性）"""
        return self.sell_order.id


class TradingPair(BaseModel):
    """交易对模型"""

    base_asset: AssetType
    """基础资产"""
    quote_asset: AssetType
    """计价资产"""
    current_price: float = Field(gt=0)
    """当前价格"""
    last_update: datetime = Field(default_factory=datetime.now)
    """最后更新时间"""

    @property
    def symbol(self) -> str:
        """交易对符号"""
        return f'{self.base_asset.value}/{self.quote_asset.value}'
