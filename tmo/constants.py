"""常量定义模块

该模块集中定义所有枚举类型，便于统一管理和维护。
"""

from enum import StrEnum


class AssetType(StrEnum):
    """资产类型枚举"""

    USDT = 'USDT'
    BTC = 'BTC'
    ETH = 'ETH'

    @property
    def initial_value(self) -> float:
        """获取资产的初始价值（以USDT为基准）"""
        return {
            AssetType.USDT: 1.0,  # USDT初始价值为1 USDT
            AssetType.BTC: 50000.0,  # BTC初始价值为50000 USDT
            AssetType.ETH: 3000.0,  # ETH初始价值为3000 USDT
        }[self]


class OrderType(StrEnum):
    """订单类型枚举"""

    BUY = 'buy'
    SELL = 'sell'
    MARKET_BUY = 'market_buy'
    MARKET_SELL = 'market_sell'


class TradingPairType(StrEnum):
    """交易对类型枚举"""

    BTC_USDT = 'BTC/USDT'
    ETH_USDT = 'ETH/USDT'
    ETH_BTC = 'ETH/BTC'

    @property
    def base_asset(self) -> AssetType:
        """获取基础资产"""
        base_symbol = self.value.split('/')[0]
        return AssetType(base_symbol)

    @property
    def quote_asset(self) -> AssetType:
        """获取计价资产"""
        quote_symbol = self.value.split('/')[1]
        return AssetType(quote_symbol)

    @property
    def initial_price(self) -> float:
        """获取初始价格"""
        return self.base_asset.initial_value / self.quote_asset.initial_value


class OrderStatus(StrEnum):
    """订单状态枚举"""

    PENDING = 'pending'
    PARTIALLY_FILLED = 'partially_filled'
    FILLED = 'filled'
    CANCELLED = 'cancelled'
