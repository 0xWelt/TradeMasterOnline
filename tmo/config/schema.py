"""配置模型：YAML → Pydantic。"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator


class AssetConfig(BaseModel):
    """资产配置。"""

    symbol: str


class PairConfig(BaseModel):
    """交易对配置。"""

    id: str
    base: str
    quote: str
    initial_price: float = Field(gt=0)
    tick_size: float = Field(gt=0)
    step_size: float = Field(gt=0)
    min_notional: float = Field(gt=0)
    n_levels: int = Field(gt=0)
    default_stp_mode: str = 'expire_maker'


class FeeConfig(BaseModel):
    """手续费配置。"""

    maker_fee: float = Field(ge=0)
    taker_fee: float = Field(ge=0)


class ExchangeConfig(BaseModel):
    """交易所配置。"""

    assets: list[AssetConfig]
    pairs: list[PairConfig]
    fees: FeeConfig

    @model_validator(mode='after')
    def _check_assets_referenced(self) -> ExchangeConfig:
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
    initial_holdings: dict[str, float] | list[dict[str, float]]
    max_qty: float = Field(gt=0)

    @model_validator(mode='after')
    def _check_holdings_length(self) -> AgentConfig:
        if isinstance(self.initial_holdings, list) and len(self.initial_holdings) != self.n_agents:
            raise ValueError(
                f'initial_holdings list length ({len(self.initial_holdings)}) '
                f'must equal n_agents ({self.n_agents})',
            )
        return self


class EnvConfig(BaseModel):
    """环境配置。"""

    max_steps: int = Field(gt=0)
    check_negative_equity: bool = False


class ConfigSchema(BaseModel):
    """完整配置模型。"""

    exchange: ExchangeConfig
    agents: AgentConfig
    env: EnvConfig

    @classmethod
    def from_yaml(cls, path: str) -> ConfigSchema:
        """从 YAML 文件加载配置。"""
        data = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
        return cls.model_validate(data)
