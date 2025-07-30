"""常量定义模块

该模块集中定义所有枚举类型，便于统一管理和维护。
"""

from __future__ import annotations

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

    @property
    def trading_pairs(self) -> list[TradingPairType]:
        """获取与该资产相关的所有交易对"""
        return [
            pair for pair in TradingPairType if pair.base_asset == self or pair.quote_asset == self
        ]


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
    """交易对类型枚举"""

    BTC_USDT = 'BTC/USDT'
    ETH_USDT = 'ETH/USDT'
    ETH_BTC = 'ETH/BTC'

    @property
    def base_asset(self) -> AssetType:
        """获取基础资产类型"""
        base, _ = self.value.split('/')
        return AssetType(base)

    @property
    def quote_asset(self) -> AssetType:
        """获取计价资产类型"""
        _, quote = self.value.split('/')
        return AssetType(quote)

    @property
    def initial_price(self) -> float:
        """获取交易对的初始价格，根据资产初始价格计算"""
        base_asset = self.base_asset
        quote_asset = self.quote_asset

        # 计算汇率：基础资产价格 / 计价资产价格
        return base_asset.initial_value / quote_asset.initial_value
