"""交易所核心数据模型。

该模块定义了交易所系统中使用的所有核心数据模型，包括资产、用户、订单、交易等。
所有模型都使用Pydantic进行数据验证和序列化。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from .constants import AssetType, OrderStatus, OrderType, TradingPairType


class Asset(BaseModel):
    """资产模型。

    表示交易所支持的数字资产，包含资产的基本信息和描述。
    """

    model_config = {'extra': 'forbid'}

    symbol: AssetType = Field(frozen=True)
    """资产类型枚举值。"""

    name: str = Field(frozen=True)
    """资产的完整名称。"""

    description: str = ''
    """资产的详细描述信息。"""


class Order(BaseModel):
    """订单模型。

    表示用户在交易所提交的买卖订单，包含订单的所有详细信息和状态。
    """

    model_config = {'extra': 'forbid'}

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), frozen=True)
    """订单唯一标识符，由系统自动生成UUID。"""

    user_id: str = Field(frozen=True)
    """下单用户的唯一标识符。"""

    order_type: OrderType = Field(frozen=True)
    """订单类型，包括限价买入、限价卖出、市价买入、市价卖出。"""

    trading_pair: TradingPairType = Field(frozen=True)
    """交易对类型，指定交易的基础资产和计价资产。"""

    base_amount: float | None = Field(default=None, frozen=True)
    """基础资产数量，对应目标货币的数量。"""

    price: float | None = Field(default=None, frozen=True)
    """订单价格，限价订单使用，市价订单不能指定。"""

    quote_amount: float | None = Field(default=None, frozen=True)
    """计价资产金额，对应计价货币的金额。"""

    timestamp: datetime = Field(default_factory=datetime.now, frozen=True)
    """订单创建时间。"""

    filled_base_amount: float = Field(default=0, ge=0)
    """已成交基础资产数量，初始为0。"""

    filled_quote_amount: float = Field(default=0, ge=0)
    """已成交计价资产金额，用于计算实际平均成交价格。"""

    average_execution_price: float = Field(default=0, ge=0)
    """实际平均成交价格，根据实际成交情况计算。"""

    status: OrderStatus = Field(default=OrderStatus.PENDING)
    """订单状态，包括待成交、部分成交、已成交、已取消。"""

    @field_validator('id', 'timestamp', mode='before')
    @classmethod
    def _validate_auto_generated_fields(cls, v: object, info: ValidationInfo) -> object:
        """验证自动生成的字段。

        对于系统自动生成的字段（id和timestamp），忽略用户提供的值，
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
            elif info.field_name == 'timestamp':
                return datetime.now()
        return v

    @field_validator('base_amount', 'quote_amount')
    @classmethod
    def _validate_amount_fields(cls, v: float | None, info: ValidationInfo) -> float | None:
        """验证基础资产数量和计价资产金额的有效性。

        确保设置的金额值大于0。

        Args:
            v: 字段值。
            info: 验证信息，包含字段名等上下文。

        Returns:
            float | None: 验证后的字段值。

        Raises:
            ValueError: 当设置值不大于0时。
        """
        if v is not None and v <= 0:
            field_name = info.field_name
            if field_name == 'base_amount':
                raise ValueError('基础资产数量必须大于0')
            elif field_name == 'quote_amount':
                raise ValueError('计价资产金额必须大于0')
        return v

    @field_validator('price')
    @classmethod
    def _validate_price(cls, v: float | None, info: ValidationInfo) -> float | None:
        """验证订单价格的合理性。

        确保限价订单必须指定大于0的价格，市价订单不能指定价格。

        Args:
            v: 字段值。
            info: 验证信息，包含字段名等上下文。

        Returns:
            float | None: 验证后的字段值。

        Raises:
            ValueError: 当价格验证失败时。
        """
        values = info.data
        order_type = values.get('order_type')

        if order_type is None:
            return v

        # 限价订单必须指定大于0的价格
        if order_type in [OrderType.BUY, OrderType.SELL]:
            if v is None:
                raise ValueError('限价订单必须指定价格')
            if v <= 0:
                raise ValueError('限价订单价格必须大于0')
        # 市价订单不能指定价格
        elif order_type in [OrderType.MARKET_BUY, OrderType.MARKET_SELL]:
            if v is not None:
                raise ValueError('市价订单不能指定价格')

        return v

    @model_validator(mode='after')
    def _validate_order_parameters(self) -> Order:
        """验证订单参数完整性。

        整合所有订单验证逻辑，确保参数一致性。

        Returns:
            Order: 验证后的订单对象。

        Raises:
            ValueError: 当参数不合法时。
        """
        # 确保基础资产数量和计价资产金额有且仅有一个被设置
        if self.base_amount is not None and self.quote_amount is not None:
            raise ValueError('基础资产数量和计价资产金额只能设置一个')

        if self.base_amount is None and self.quote_amount is None:
            raise ValueError('订单必须指定基础资产数量或计价资产金额')

        return self

    @property
    def remaining_base_amount(self) -> float:
        """剩余基础资产数量。

        Returns:
            float: 订单总基础资产数量减去已成交基础资产数量。
        """
        if self.base_amount is None:
            return 0.0
        return self.base_amount - self.filled_base_amount

    @property
    def remaining_quote_amount(self) -> float:
        """剩余计价资产金额。

        Returns:
            float: 订单总计价资产金额减去已成交计价资产金额。
        """
        if self.quote_amount is None:
            return 0.0
        return self.quote_amount - self.filled_quote_amount

    @property
    def is_filled(self) -> bool:
        """是否完全成交。

        Returns:
            bool: 当已成交数量达到订单设定目标时返回True。
        """
        if self.base_amount is not None:
            return self.filled_base_amount >= self.base_amount
        if self.quote_amount is not None:
            return self.filled_quote_amount >= self.quote_amount
        return False

    @property
    def is_partially_filled(self) -> bool:
        """是否部分成交。

        Returns:
            bool: 当已成交数量大于0但小于订单设定目标时返回True。
        """
        if self.base_amount is not None:
            return 0 < self.filled_base_amount < self.base_amount
        if self.quote_amount is not None:
            return 0 < self.filled_quote_amount < self.quote_amount
        return False


class TradeSettlement(BaseModel):
    """交易结算统计信息。

    表示一次完整的交易撮合结果，记录买卖双方的订单信息和成交详情。
    """

    model_config = {'extra': 'forbid'}

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), frozen=True)
    """交易唯一标识符，由系统自动生成UUID。"""

    buy_order: Order = Field(frozen=True)
    """买单对象，包含完整的买单信息。"""

    sell_order: Order = Field(frozen=True)
    """卖单对象，包含完整的卖单信息。"""

    trading_pair: TradingPairType = Field(frozen=True)
    """交易对类型，指定交易的基础资产和计价资产。"""

    base_amount: float = Field(gt=0, frozen=True)
    """成交基础资产数量，表示实际成交的基础资产数量。"""

    price: float = Field(gt=0, frozen=True)
    """成交价格，以计价资产表示的单价。"""

    timestamp: datetime = Field(default_factory=datetime.now, frozen=True)
    """成交时间，记录交易发生的时间戳。"""

    @field_validator('id', 'timestamp', mode='before')
    @classmethod
    def _validate_auto_generated_fields(cls, v: object, info: ValidationInfo) -> object:
        """验证自动生成的字段。

        对于系统自动生成的字段（id和timestamp），忽略用户提供的值，
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
            elif info.field_name == 'timestamp':
                return datetime.now()
        return v

    @property
    def buy_order_id(self) -> str:
        """获取买单ID（兼容性属性）。

        Returns:
            str: 买单的唯一标识符。
        """
        return self.buy_order.id

    @property
    def sell_order_id(self) -> str:
        """获取卖单ID（兼容性属性）。

        Returns:
            str: 卖单的唯一标识符。
        """
        return self.sell_order.id
