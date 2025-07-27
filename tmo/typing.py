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


class Portfolio(BaseModel):
    """用户持仓模型。

    表示用户在特定资产上的持仓情况，包括可用余额、锁定余额和总余额。
    """

    model_config = {'extra': 'forbid'}

    asset: AssetType = Field(frozen=True)
    """资产类型枚举值。"""

    available_balance: float = Field(default=0, ge=0)
    """可用余额，可用于下单或提现的金额。"""

    locked_balance: float = Field(default=0, ge=0)
    """锁定余额，已被订单占用但尚未成交的金额。"""

    total_balance: float = Field(default=0, ge=0)
    """总余额，等于可用余额加锁定余额。"""


class User(BaseModel):
    """用户模型。

    表示交易所系统中的用户，包含用户基本信息和资产持仓。
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

    portfolios: dict[AssetType, Portfolio] = Field(default_factory=dict)
    """用户资产持仓字典，键为资产类型，值为持仓信息。"""

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

    def update_balance(
        self, asset: AssetType, available_change: float, locked_change: float
    ) -> None:
        """更新用户资产余额。

        用于增加或减少用户的可用余额和锁定余额。如果资产不存在，会自动创建新的持仓记录。

        Args:
            asset: 要更新的资产类型。
            available_change: 可用余额的变化量，正值表示增加，负值表示减少。
            locked_change: 锁定余额的变化量，正值表示增加，负值表示减少。

        Example:
            >>> user.update_balance(AssetType.BTC, 1.5, -1.0)
            # 增加1.5 BTC可用余额，减少1.0 BTC锁定余额
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
    """订单模型。

    表示用户在交易所提交的买卖订单，包含订单的所有详细信息和状态。
    """

    model_config = {'extra': 'forbid'}

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), frozen=True)
    """订单唯一标识符，由系统自动生成UUID。"""

    user: User = Field(frozen=True)
    """下单用户的完整对象引用。"""

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
        # 检查设置值必须大于0
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
        # 获取订单类型
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
    def _validate_amount_mutual_exclusion(self) -> Order:
        """验证基础资产数量和计价资产金额的互斥性。

        确保基础资产数量和计价资产金额有且仅有一个被设置。

        Returns:
            Order: 验证后的订单对象。

        Raises:
            ValueError: 当两个字段都设置或都未设置时。
        """
        if self.base_amount is not None and self.quote_amount is not None:
            raise ValueError('基础资产数量和计价资产金额只能设置一个')

        if self.base_amount is None and self.quote_amount is None:
            raise ValueError('必须设置基础资产数量或计价资产金额')

        return self

    @property
    def user_id(self) -> str:
        """获取用户ID（兼容性属性）。

        Returns:
            str: 下单用户的唯一标识符。
        """
        return self.user.id

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
    def is_filled(self) -> bool:
        """是否完全成交。

        Returns:
            bool: 当已成交基础资产数量大于等于订单基础资产数量时返回True。
        """
        if self.base_amount is None:
            return False
        return self.filled_base_amount >= self.base_amount

    @property
    def is_partially_filled(self) -> bool:
        """是否部分成交。

        Returns:
            bool: 当已成交基础资产数量大于0且小于订单基础资产数量时返回True。
        """
        if self.base_amount is None:
            return False
        return 0 < self.filled_base_amount < self.base_amount

    def on_filled(self, trade: TradeSettlement) -> None:
        """订单成交时的回调方法（已废弃）。

        用户持仓更新已移动到TradeSettlement层面处理。
        """

    def on_cancelled(self) -> None:
        """订单取消时的回调方法。

        当订单被取消时，释放被该订单锁定的资产。
        """
        if self.user is None:
            return

        if self.order_type == OrderType.BUY:
            # 释放锁定的计价资产
            if self.price is not None and self.base_amount is not None:
                locked_amount = self.remaining_base_amount * self.price
            elif self.quote_amount is not None:
                # 对于使用quote_amount的订单，释放全部quote_amount
                locked_amount = self.quote_amount
            else:
                locked_amount = 0.0

            self.user.update_balance(
                asset=AssetType(self.trading_pair.quote_asset.value),
                available_change=locked_amount,
                locked_change=-locked_amount,
            )
        else:
            # 释放锁定的基础资产
            if self.base_amount is not None:
                locked_amount = self.remaining_base_amount
            else:
                # 对于使用quote_amount的卖单，需要计算基础资产数量
                locked_amount = 0.0  # 这种情况应在交易引擎中处理

            self.user.update_balance(
                asset=AssetType(self.trading_pair.base_asset.value),
                available_change=locked_amount,
                locked_change=-locked_amount,
            )


class TradeSettlement(BaseModel):
    """交易结算统计信息。

    表示一次完整的交易撮合结果，记录买卖双方的订单信息和成交详情。
    """

    model_config = {'extra': 'forbid'}

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

    @field_validator('timestamp', mode='before')
    @classmethod
    def _validate_auto_generated_fields(cls, v: object, info: ValidationInfo) -> object:
        """验证自动生成的字段。

        对于系统自动生成的timestamp字段，忽略用户提供的值，
        始终使用系统默认值。

        Args:
            v: 字段值，如果为None则使用默认值。
            info: 验证信息，包含字段名等上下文。

        Returns:
            object: 处理后的字段值。
        """
        if v is not None and info.field_name == 'timestamp':
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
