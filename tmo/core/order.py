"""订单与成交数据模型。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from tmo.utils.types import AgentId, OrderId, PairId


class Side(StrEnum):
    """交易方向枚举。"""

    HOLD = 'HOLD'
    """观望（不下单）。"""
    BUY = 'BUY'
    """买入。"""
    SELL = 'SELL'
    """卖出。"""


class TimeInForce(StrEnum):
    """订单有效期策略（参考 Binance GTC/IOC/FOK）。"""

    GTC = 'GTC'
    """Good Till Cancelled：一直有效直到取消。"""
    IOC = 'IOC'
    """Immediate or Cancel：立即成交剩余取消。"""
    FOK = 'FOK'
    """Fill or Kill：全部成交否则取消。"""


class OrderStatus(StrEnum):
    """订单生命周期状态（参考 Binance / 主流交易所）。"""

    NEW = 'NEW'
    """新建，尚未成交。"""
    PARTIALLY_FILLED = 'PARTIALLY_FILLED'
    """部分成交。"""
    FILLED = 'FILLED'
    """完全成交。"""
    CANCELED = 'CANCELED'
    """已被取消（用户主动撤单或 OCO 触发）。"""
    EXPIRED = 'EXPIRED'
    """已过期（IOC/FOK 规则或 STP 触发）。"""
    REJECTED = 'REJECTED'
    """被拒绝（filter 失败或余额不足）。"""


class Order(BaseModel):
    """限价订单数据模型。"""

    model_config = {'frozen': True}

    order_id: OrderId
    """订单唯一标识。"""
    agent_id: AgentId
    """下单智能体标识。"""
    pair_id: PairId
    """交易对标识。"""
    side: Side
    """交易方向。"""
    price: float = Field(gt=0)
    """限价，必须大于 0。"""
    quantity: float = Field(gt=0)
    """数量，必须大于 0。"""
    time_in_force: TimeInForce = TimeInForce.GTC
    """订单有效期策略，默认 GTC。"""
    stp_mode: str | None = None
    """自成交保护策略（None 表示使用交易对默认值）。"""
    status: OrderStatus = OrderStatus.NEW
    """订单当前状态，默认 NEW。"""
    filled_qty: float = 0.0
    """已成交数量，默认 0。"""

    def is_buy(self) -> bool:
        """判断是否为买单。

        Returns:
            True 当且仅当 side 为 BUY。
        """
        return self.side is Side.BUY

    def is_sell(self) -> bool:
        """判断是否为卖单。

        Returns:
            True 当且仅当 side 为 SELL。
        """
        return self.side is Side.SELL


class Trade(BaseModel):
    """成交记录数据模型。"""

    model_config = {'frozen': True}

    pair_id: PairId
    """成交发生的交易对。"""
    price: float = Field(gt=0)
    """成交价格，必须大于 0。"""
    quantity: float = Field(gt=0)
    """成交数量，必须大于 0。"""
    buyer_id: AgentId
    """买方智能体标识。"""
    seller_id: AgentId
    """卖方智能体标识。"""
    buy_order_id: OrderId
    """买方订单标识。"""
    sell_order_id: OrderId
    """卖方订单标识。"""

    @property
    def notional(self) -> float:
        """成交金额。

        Returns:
            price * quantity。
        """
        return self.price * self.quantity

    @model_validator(mode='after')
    def _check_ids(self) -> Trade:
        """验证买卖双方不能为同一智能体（自成交保护）。

        Raises:
            ValueError: 当 buyer_id 与 seller_id 相同时抛出。
        """
        if self.buyer_id == self.seller_id:
            raise ValueError('buyer and seller must be different')
        return self
