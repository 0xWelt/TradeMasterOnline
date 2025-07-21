"""交易所核心数据模型"""

from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class AssetType(str, Enum):
    """资产类型"""
    USDT = 'USDT'
    BTC = 'BTC'


class OrderType(str, Enum):
    """订单类型"""
    BUY = 'buy'
    SELL = 'sell'


class Asset(BaseModel):
    """资产模型"""
    symbol: AssetType
    name: str
    description: str = ''


class Order(BaseModel):
    """订单模型"""
    id: str = Field(description='订单唯一标识')
    user_id: str = Field(description='用户ID')
    order_type: OrderType = Field(description='订单类型：买入或卖出')
    asset: AssetType = Field(description='交易资产')
    quantity: float = Field(gt=0, description='数量')
    price: float = Field(gt=0, description='价格')
    timestamp: datetime = Field(default_factory=datetime.now, description='创建时间')
    filled_quantity: float = Field(default=0, description='已成交数量')
    status: str = Field(default='pending', description='订单状态')
    
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


class Trade(BaseModel):
    """成交记录模型"""
    id: str = Field(description='成交记录唯一标识')
    buy_order_id: str = Field(description='买单ID')
    sell_order_id: str = Field(description='卖单ID')
    asset: AssetType = Field(description='交易资产')
    quantity: float = Field(gt=0, description='成交数量')
    price: float = Field(gt=0, description='成交价格')
    timestamp: datetime = Field(default_factory=datetime.now, description='成交时间')


class TradingPair(BaseModel):
    """交易对模型"""
    base_asset: AssetType = Field(description='基础资产')
    quote_asset: AssetType = Field(description='计价资产')
    current_price: float = Field(gt=0, description='当前价格')
    last_update: datetime = Field(default_factory=datetime.now, description='最后更新时间')
    
    @property
    def symbol(self) -> str:
        """交易对符号"""
        return f'{self.base_asset.value}/{self.quote_asset.value}' 