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


class OrderStatus(StrEnum):
    """订单状态枚举"""

    PENDING = 'pending'
    PARTIALLY_FILLED = 'partially_filled'
    FILLED = 'filled'
    CANCELLED = 'cancelled'


class TradingPairType(StrEnum):
    """交易对类型枚举

    定义所有支持的交易对，包含基础资产和计价资产的组合。
    使用字符串枚举确保类型安全和可读性。

    Attributes:
        BTC_USDT: 比特币/泰达币交易对，以USDT计价
        ETH_USDT: 以太坊/泰达币交易对，以USDT计价
        ETH_BTC: 以太坊/比特币交易对，以BTC计价
    """

    BTC_USDT = 'BTC_USDT'
    ETH_USDT = 'ETH_USDT'
    ETH_BTC = 'ETH_BTC'

    @property
    def base_asset(self) -> AssetType:
        """获取基础资产类型"""
        return {
            TradingPairType.BTC_USDT: AssetType.BTC,
            TradingPairType.ETH_USDT: AssetType.ETH,
            TradingPairType.ETH_BTC: AssetType.ETH,
        }[self]

    @property
    def quote_asset(self) -> AssetType:
        """获取计价资产类型"""
        return {
            TradingPairType.BTC_USDT: AssetType.USDT,
            TradingPairType.ETH_USDT: AssetType.USDT,
            TradingPairType.ETH_BTC: AssetType.BTC,
        }[self]

    @property
    def initial_price(self) -> float:
        """获取交易对的初始价格"""
        return {
            TradingPairType.BTC_USDT: 50000.0,  # 1 BTC = 50000 USDT
            TradingPairType.ETH_USDT: 3000.0,  # 1 ETH = 3000 USDT
            TradingPairType.ETH_BTC: 0.06,  # 1 ETH = 0.06 BTC
        }[self]
