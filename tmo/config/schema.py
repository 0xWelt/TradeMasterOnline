"""配置模型：YAML → Pydantic。"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator


class AssetConfig(BaseModel):
    """资产配置。"""

    symbol: str
    """资产符号（如 BTC、USDT）。"""


class PairConfig(BaseModel):
    """交易对配置。"""

    id: str
    """交易对唯一标识（如 BTC/USDT）。"""

    base: str
    """基础资产符号。"""

    quote: str
    """计价资产符号。"""

    initial_price: float = Field(gt=0)
    """初始价格，必须大于 0。"""

    tick_size: float = Field(gt=0)
    """价格步长（filter 校验用），必须大于 0。"""

    step_size: float = Field(gt=0)
    """数量步长（filter 校验用），必须大于 0。"""

    min_notional: float = Field(gt=0)
    """最小名义价值（filter 校验用），必须大于 0。"""

    n_levels: int = Field(gt=0)
    """订单簿观测档位数，必须大于 0。"""

    default_stp_mode: str = Field(
        default='expire_maker',
        pattern='^(expire_maker|expire_taker|expire_both|none)$',
    )
    """默认自成交保护策略，可选 expire_maker / expire_taker / expire_both / none。"""


class FeeConfig(BaseModel):
    """手续费配置。"""

    maker_fee: float = Field(ge=0)
    """Maker 手续费率，必须大于等于 0。"""

    taker_fee: float = Field(ge=0)
    """Taker 手续费率，必须大于等于 0。"""

    base_precision: int = Field(default=8, ge=0)
    """Base 资产精度（截断位数），默认 8，必须大于等于 0。"""

    quote_precision: int = Field(default=8, ge=0)
    """Quote 资产精度（截断位数），默认 8，必须大于等于 0。"""


class ExchangeConfig(BaseModel):
    """交易所配置。"""

    assets: list[AssetConfig]
    """资产列表。"""

    pairs: list[PairConfig]
    """交易对列表。"""

    fees: FeeConfig
    """手续费配置。"""

    @model_validator(mode='after')
    def _check_assets_referenced(self) -> ExchangeConfig:
        """验证所有交易对的 base 和 quote 资产都存在于资产列表中。

        Returns:
            验证通过后的 ExchangeConfig 实例。

        Raises:
            ValueError: 当某个交易对引用了不存在的资产时抛出。
        """
        symbols = {a.symbol for a in self.assets}
        for pair in self.pairs:
            if pair.base not in symbols:
                raise ValueError(f'pair {pair.id} base {pair.base} not in assets')
            if pair.quote not in symbols:
                raise ValueError(f'pair {pair.id} quote {pair.quote} not in assets')
        return self


class AgentConfig(BaseModel):
    """智能体配置。"""

    n_agents: int = Field(gt=0)
    """智能体数量，必须大于 0。"""

    initial_holdings: dict[str, float] | list[dict[str, float]]
    """初始持仓，支持统一 dict（所有 agent 相同）或 per-agent list[dict]。"""

    max_qty: float = Field(gt=0)
    """单次最大下单数量，必须大于 0。"""

    @model_validator(mode='after')
    def _check_holdings_length(self) -> AgentConfig:
        """当 initial_holdings 为 list 时，验证长度等于 n_agents。

        Returns:
            验证通过后的 AgentConfig 实例。

        Raises:
            ValueError: 当 list 长度不等于 n_agents 时抛出。
        """
        if isinstance(self.initial_holdings, list) and len(self.initial_holdings) != self.n_agents:
            raise ValueError(
                f'initial_holdings list length ({len(self.initial_holdings)}) '
                f'must equal n_agents ({self.n_agents})',
            )
        return self


class EnvConfig(BaseModel):
    """环境配置。"""

    max_steps: int = Field(gt=0)
    """每轮最大步数，必须大于 0。"""

    check_negative_equity: bool = False
    """是否检查负资产并触发终止，默认 False。"""


class ConfigSchema(BaseModel):
    """完整配置模型。"""

    exchange: ExchangeConfig
    """交易所配置。"""

    agents: AgentConfig
    """智能体配置。"""

    env: EnvConfig
    """环境配置。"""

    @classmethod
    def from_yaml(cls, path: str) -> ConfigSchema:
        """从 YAML 文件加载配置。

        Args:
            path: YAML 文件路径。

        Returns:
            解析后的 ConfigSchema 实例。
        """
        data = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
        return cls.model_validate(data)
