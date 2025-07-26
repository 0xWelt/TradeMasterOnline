"""交易所核心数据模型。

该模块定义了交易所系统中使用的所有核心数据模型，包括资产、用户、订单、交易等。
所有模型都使用Pydantic进行数据验证和序列化。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from .constants import AssetType, OrderStatus, OrderType, TradingPairType


class Asset(BaseModel):
    """资产模型。

    表示交易所支持的数字资产，包含资产的基本信息和描述。

    Attributes:
        symbol: 资产类型枚举值，如USDT、BTC、ETH等。
        name: 资产的完整名称，如"Tether USD"。
        description: 资产的详细描述信息。
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

    Attributes:
        asset: 资产类型枚举值，表示该持仓对应的资产。
        available_balance: 可用余额，可用于下单或提现的金额。
        locked_balance: 锁定余额，已被订单占用但尚未成交的金额。
        total_balance: 总余额，等于可用余额加锁定余额。
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

    Attributes:
        id: 用户唯一标识符，由系统自动生成UUID。
        username: 用户名，具有唯一性。
        email: 用户邮箱地址，用于联系和验证。
        created_at: 用户创建时间，记录注册时间。
        portfolios: 用户资产持仓字典，键为资产类型，值为持仓信息。
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

    Attributes:
        id: 订单唯一标识符，由系统自动生成UUID。
        user: 下单用户的完整对象引用。
        order_type: 订单类型，包括限价买入、限价卖出、市价买入、市价卖出。
        trading_pair: 交易对类型，指定交易的基础资产和计价资产。
        quantity: 订单数量，对应目标货币的数量。
        price: 订单价格，限价订单使用，市价订单为0。
        amount: 订单金额，对应计价货币的金额，用于市价订单。
        timestamp: 订单创建时间。
        filled_quantity: 已成交数量，初始为0。
        status: 订单状态，包括待成交、部分成交、已成交、已取消。
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

    quantity: float = Field(gt=0, frozen=True)
    """订单数量，对应目标货币的数量。"""

    price: float = Field(ge=0, frozen=True)
    """订单价格，限价订单使用，市价订单为0。"""

    amount: float = Field(default=0, ge=0, frozen=True)
    """订单金额，对应计价货币的金额，用于市价订单。"""

    timestamp: datetime = Field(default_factory=datetime.now, frozen=True)
    """订单创建时间。"""

    filled_quantity: float = Field(default=0, ge=0)
    """已成交数量，初始为0。"""

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

    @property
    def user_id(self) -> str:
        """获取用户ID（兼容性属性）。

        Returns:
            str: 下单用户的唯一标识符。
        """
        return self.user.id

    @property
    def remaining_quantity(self) -> float:
        """剩余未成交数量。

        Returns:
            float: 订单总数减去已成交数量。
        """
        return self.quantity - self.filled_quantity

    @property
    def is_filled(self) -> bool:
        """是否完全成交。

        Returns:
            bool: 当已成交数量大于等于订单数量时返回True。
        """
        return self.filled_quantity >= self.quantity

    @property
    def is_partially_filled(self) -> bool:
        """是否部分成交。

        Returns:
            bool: 当已成交数量大于0且小于订单数量时返回True。
        """
        return 0 < self.filled_quantity < self.quantity

    def on_filled(self, trade: TradeSettlement) -> None:
        """订单成交时的回调方法。

        根据订单类型更新用户资产余额，实现资产交割。

        Args:
            trade: 成交结算信息，包含成交数量和价格。
        """
        if self.order_type == OrderType.BUY:
            # 买单：获得基础资产，减少计价资产
            self.user.update_balance(
                asset=self.trading_pair.base_asset,
                available_change=trade.quantity,
                locked_change=-trade.quantity,
            )
            self.user.update_balance(
                asset=self.trading_pair.quote_asset,
                available_change=-trade.quantity * trade.price,
                locked_change=0,
            )
        else:
            # 卖单：获得计价资产，减少基础资产
            self.user.update_balance(
                asset=self.trading_pair.quote_asset,
                available_change=trade.quantity * trade.price,
                locked_change=0,
            )
            self.user.update_balance(
                asset=self.trading_pair.base_asset,
                available_change=0,
                locked_change=-trade.quantity,
            )

    def on_cancelled(self) -> None:
        """订单取消时的回调方法。

        当订单被取消时，释放被该订单锁定的资产。
        """
        if self.user is None:
            return

        if self.order_type == OrderType.BUY:
            # 释放锁定的计价资产
            locked_amount = self.remaining_quantity * self.price
            self.user.update_balance(
                asset=AssetType(self.trading_pair.quote_asset.value),
                available_change=locked_amount,
                locked_change=-locked_amount,
            )
        else:
            # 释放锁定的基础资产
            self.user.update_balance(
                asset=AssetType(self.trading_pair.base_asset.value),
                available_change=self.remaining_quantity,
                locked_change=-self.remaining_quantity,
            )


class TradeSettlement(BaseModel):
    """交易结算统计信息。

    表示一次完整的交易撮合结果，记录买卖双方的订单信息和成交详情。

    Attributes:
        buy_order: 买单对象，包含完整的买单信息。
        sell_order: 卖单对象，包含完整的卖单信息。
        trading_pair: 交易对类型，指定交易的基础资产和计价资产。
        quantity: 成交数量，表示实际成交的基础资产数量。
        price: 成交价格，以计价资产表示的单价。
        timestamp: 成交时间，记录交易发生的时间戳。
    """

    model_config = {'extra': 'forbid'}

    buy_order: Order = Field(frozen=True)
    """买单对象，包含完整的买单信息。"""

    sell_order: Order = Field(frozen=True)
    """卖单对象，包含完整的卖单信息。"""

    trading_pair: TradingPairType = Field(frozen=True)
    """交易对类型，指定交易的基础资产和计价资产。"""

    quantity: float = Field(gt=0, frozen=True)
    """成交数量，表示实际成交的基础资产数量。"""

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


class TradingPair(BaseModel):
    """交易对模型。

    表示交易对的基本信息，包含基础资产、计价资产和当前市场价格。

    Attributes:
        base_asset: 基础资产类型，如BTC、ETH等。
        quote_asset: 计价资产类型，如USDT等稳定币。
        current_price: 当前市场价格，表示1个基础资产对应的计价资产数量。
        last_update: 最后更新时间，记录价格最后一次变动的时间。
    """

    base_asset: AssetType = Field(frozen=True)
    """基础资产类型，如BTC、ETH等。"""

    quote_asset: AssetType = Field(frozen=True)
    """计价资产类型，如USDT等稳定币。"""

    current_price: float = Field(gt=0)
    """当前市场价格，表示1个基础资产对应的计价资产数量。"""

    last_update: datetime = Field(default_factory=datetime.now)
    """最后更新时间，记录价格最后一次变动的时间。"""

    @property
    def symbol(self) -> str:
        """交易对符号。

        返回交易对的标准符号表示，格式为"基础资产/计价资产"。

        Returns:
            str: 交易对符号，如"BTC/USDT"。
        """
        return f'{self.base_asset.value}/{self.quote_asset.value}'
