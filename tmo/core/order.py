"""订单与成交数据模型。"""

from __future__ import annotations

from enum import Enum, StrEnum

from pydantic import BaseModel, Field, model_validator

from tmo.utils.types import AgentId, OrderId, PairId


class Side(Enum):
    """交易方向。"""

    HOLD = 0
    BUY = 1
    SELL = 2


class TimeInForce(StrEnum):
    """订单有效期策略（参考 Binance GTC/IOC/FOK）。"""

    GTC = 'GTC'
    IOC = 'IOC'
    FOK = 'FOK'


class Order(BaseModel):
    """限价订单。"""

    model_config = {'frozen': True}

    order_id: OrderId
    agent_id: AgentId
    pair_id: PairId
    side: Side
    price: float = Field(gt=0)
    quantity: float = Field(gt=0)
    time_in_force: TimeInForce = TimeInForce.GTC

    def is_buy(self) -> bool:
        """是否为买单。"""
        return self.side is Side.BUY

    def is_sell(self) -> bool:
        """是否为卖单。"""
        return self.side is Side.SELL


class Trade(BaseModel):
    """成交记录。"""

    model_config = {'frozen': True}

    pair_id: PairId
    price: float = Field(gt=0)
    quantity: float = Field(gt=0)
    buyer_id: AgentId
    seller_id: AgentId
    buy_order_id: OrderId
    sell_order_id: OrderId

    @property
    def notional(self) -> float:
        """成交金额。"""
        return self.price * self.quantity

    @model_validator(mode='after')
    def _check_ids(self) -> Trade:
        if self.buyer_id == self.seller_id:
            raise ValueError('buyer and seller must be different')
        return self
