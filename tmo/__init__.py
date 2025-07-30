"""TradeMasterOnline - 多人在线交易模拟游戏"""

__version__ = '0.1.0'
__author__ = 'TradeMasterOnline Team'

from .constants import AssetType, OrderStatus, OrderType, TradingPairType
from .exchange import Exchange
from .typing import Asset, Order, TradeSettlement
from .user import User


# 重建用户模型以解决前向引用问题
User.model_rebuild()

__all__ = [
    'Asset',
    'AssetType',
    'Exchange',
    'Order',
    'OrderStatus',
    'OrderType',
    'TradeSettlement',
    'TradingPairType',
    'User',
]
