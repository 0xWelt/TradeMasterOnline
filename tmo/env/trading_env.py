"""PettingZoo AEC 交易环境。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
from gymnasium import spaces
from pettingzoo.utils.env import AECEnv

from tmo.config.schema import ConfigSchema
from tmo.core.order import Order, Side, Trade
from tmo.core.order_book import OrderBook


if TYPE_CHECKING:
    from tmo.utils.types import AgentId


class TradingEnv(AECEnv):
    """基于 AEC API 的多智能体交易仿真环境。"""

    def __init__(self, config: ConfigSchema) -> None:
        super().__init__()
        self.metadata = {'name': 'trading_env'}
        self.config = config
        self._pair_list = config.exchange.pairs
        self._pair_by_id = {p.id: p for p in self._pair_list}
        self._asset_list = config.exchange.assets
        self._pair_ids = [p.id for p in self._pair_list]
        self._asset_symbols = [a.symbol for a in self._asset_list]
        self._n_pairs = len(self._pair_list)
        self._n_assets = len(self._asset_list)
        self._n_levels = max(p.n_levels for p in self._pair_list)
        self._fee = config.exchange.fees

        self.possible_agents = [f'agent_{i}' for i in range(config.agents.n_agents)]
        self.agents: list[str] = []

        # 状态
        self.books: dict[str, OrderBook] = {}
        self.prices: dict[str, float] = {}
        self.holdings: dict[str, dict[str, float]] = {}
        self.exchange_holdings: dict[str, float] = {}

        # AEC 状态
        self.terminations: dict[str, bool] = {}
        self.truncations: dict[str, bool] = {}
        self.rewards: dict[str, float] = {}
        self._cumulative_rewards: dict[str, float] = {}
        self.infos: dict[str, dict[str, Any]] = {}
        self.agent_selection = ''

        self.step_count = 0
        self._agent_idx = 0
        self._order_counter = 0

        # spaces
        self._build_spaces()

    @classmethod
    def from_config(cls, path: str) -> TradingEnv:
        """从 YAML 配置文件创建环境。"""
        return cls(ConfigSchema.from_yaml(path))

    def _build_spaces(self) -> None:
        """构建 observation / action spaces。"""
        book_space = spaces.Dict(
            {
                p.id: spaces.Dict(
                    {
                        'bids': spaces.Box(
                            low=0,
                            high=np.inf,
                            shape=(p.n_levels, 2),
                            dtype=np.float64,
                        ),
                        'asks': spaces.Box(
                            low=0,
                            high=np.inf,
                            shape=(p.n_levels, 2),
                            dtype=np.float64,
                        ),
                    }
                )
                for p in self._pair_list
            }
        )
        holdings_space = spaces.Dict(
            {
                a.symbol: spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float64)
                for a in self._asset_list
            }
        )
        obs_space = spaces.Dict(
            {
                'books': book_space,
                'holdings': holdings_space,
            }
        )
        act_space = spaces.Dict(
            {
                'asset_id': spaces.Discrete(self._n_pairs),
                'side': spaces.Discrete(3),
                'price': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float64),
                'quantity': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float64),
            }
        )
        self.observation_spaces = dict.fromkeys(self.possible_agents, obs_space)
        self.action_spaces = dict.fromkeys(self.possible_agents, act_space)

    def reset(self, seed: int | None = None, options: dict | None = None) -> None:  # noqa: ARG002
        """重置环境。"""
        self.agents = self.possible_agents.copy()
        self.step_count = 0
        self._agent_idx = 0
        self._order_counter = 0

        # 初始化订单簿
        self.books = {p.id: OrderBook(p.id) for p in self._pair_list}

        # 初始化价格
        self.prices = {}
        for p in self._pair_list:
            self.prices[p.base] = p.initial_price
            self.prices[p.quote] = 1.0  # 计价资产基准价

        # 初始化持仓
        init_holdings = self.config.agents.initial_holdings
        if isinstance(init_holdings, list):
            self.holdings = {
                agent: {sym: init_holdings[i].get(sym, 0.0) for sym in self._asset_symbols}
                for i, agent in enumerate(self.agents)
            }
        else:
            self.holdings = {
                agent: {sym: init_holdings.get(sym, 0.0) for sym in self._asset_symbols}
                for agent in self.agents
            }

        # 交易所手续费持仓
        self.exchange_holdings = dict.fromkeys(self._asset_symbols, 0.0)

        # AEC 状态
        self.terminations = dict.fromkeys(self.agents, False)
        self.truncations = dict.fromkeys(self.agents, False)
        self.rewards = dict.fromkeys(self.agents, 0.0)
        self._cumulative_rewards = dict.fromkeys(self.agents, 0.0)
        self.infos = {a: {} for a in self.agents}
        self.agent_selection = self.agents[0]

    def observe(self, agent: AgentId) -> dict[str, Any]:
        """返回 agent 的局部观测。"""
        books_obs = {}
        for p in self._pair_list:
            snap = self.books[p.id].get_snapshot(p.n_levels)
            bids = np.array(snap['bids'], dtype=np.float64)
            asks = np.array(snap['asks'], dtype=np.float64)
            # pad to fixed shape
            bids = self._pad_levels(bids, p.n_levels)
            asks = self._pad_levels(asks, p.n_levels)
            books_obs[p.id] = {'bids': bids, 'asks': asks}
        holdings_obs = {
            sym: np.float64(self.holdings[agent].get(sym, 0.0)) for sym in self._asset_symbols
        }
        return {'books': books_obs, 'holdings': holdings_obs}

    def _pad_levels(
        self,
        arr: np.ndarray,
        n_levels: int,
    ) -> np.ndarray:
        """将快照数组填充到固定长度。"""
        if arr.ndim == 1:
            arr = arr.reshape(-1, 2)
        padded = np.zeros((n_levels, 2), dtype=np.float64)
        n = min(len(arr), n_levels)
        if n > 0:
            padded[:n] = arr[:n]
        return padded

    @staticmethod
    def _is_valid_step(value: float, step: float) -> bool:
        """检查 value 是否为 step 的整数倍（考虑浮点精度）。"""
        if step <= 0:
            return True
        ratio = value / step
        return abs(ratio - round(ratio)) < 1e-9

    def step(self, action: dict[str, Any] | None) -> None:
        """执行当前 agent 的动作。"""
        agent = self.agent_selection
        if agent not in self.agents:
            return
        if self.terminations[agent] or self.truncations[agent]:
            self._was_dead_step(action)
            return

        if action is None:
            return

        self.rewards = dict.fromkeys(self.agents, 0.0)
        self.infos = {a: {} for a in self.agents}

        side = Side(int(action['side']))
        if side is not Side.HOLD:
            pair = self._pair_list[int(action['asset_id'])]
            price = float(action['price'])
            qty = float(action['quantity'])

            # Filter 校验（参考 Binance PRICE_FILTER / LOT_SIZE / MIN_NOTIONAL）
            if not self._is_valid_step(price, pair.tick_size):
                return  # 价格不符合步长
            if not self._is_valid_step(qty, pair.step_size):
                return  # 数量不符合步长
            if price * qty < pair.min_notional:
                return  # 名义价值过低

            if self._can_place_order(agent, pair, side, price, qty):
                self._order_counter += 1
                order = Order(
                    order_id=f'{agent}_{self._order_counter}',
                    agent_id=agent,
                    pair_id=pair.id,
                    side=side,
                    price=price,
                    quantity=qty,
                )
                trades = self.books[pair.id].place_order(order)
                self._settle_trades(agent, pair, trades, side)

        self._check_terminal(agent)
        self._advance_agent()

    def _can_place_order(
        self,
        agent: AgentId,
        pair: Any,
        side: Side,
        price: float,
        qty: float,
    ) -> bool:
        """检查 agent 是否有足够资金下单（已扣除所有未成交挂单的全局占用）。"""
        if qty <= 0 or price <= 0:
            return False

        if side is Side.BUY:
            # 统计该 agent 在所有交易对上、以同一 quote 资产计价的未成交买单
            # 冻结的资金总额
            locked = 0.0
            for book in self.books.values():
                for o in book.orders.values():
                    if o.agent_id == agent and o.side is Side.BUY:
                        o_pair = self._pair_by_id[o.pair_id]
                        if o_pair.quote == pair.quote:
                            locked += o.price * o.quantity
            available = self.holdings[agent].get(pair.quote, 0.0)
            return available - locked >= price * qty

        if side is Side.SELL:
            # 统计该 agent 在所有交易对上、以同一 base 资产计价的未成交卖单
            # 冻结的 asset 总额
            locked = 0.0
            for book in self.books.values():
                for o in book.orders.values():
                    if o.agent_id == agent and o.side is Side.SELL:
                        o_pair = self._pair_by_id[o.pair_id]
                        if o_pair.base == pair.base:
                            locked += o.quantity
            available = self.holdings[agent].get(pair.base, 0.0)
            return available - locked >= qty

        return False

    def _settle_trades(
        self,
        agent: AgentId,
        pair: Any,
        trades: list[Trade],
        agent_side: Side,
    ) -> None:
        """结算成交，更新持仓和价格（Binance 模式：fee 从 received asset 扣除）。"""
        for trade in trades:
            self.prices[pair.base] = trade.price
            notional = trade.notional

            if agent_side is Side.BUY:
                # agent 是 taker buyer：支付 exact notional，收到 qty - taker_fee
                if trade.buyer_id == agent:
                    self.holdings[agent][pair.base] += trade.quantity * (1 - self._fee.taker_fee)
                    self.holdings[agent][pair.quote] -= notional
                    self.exchange_holdings[pair.base] += trade.quantity * self._fee.taker_fee
                # resting seller 是 maker：付出 qty，收到 notional - maker_fee
                if trade.seller_id in self.holdings:
                    self.holdings[trade.seller_id][pair.base] -= trade.quantity
                    self.holdings[trade.seller_id][pair.quote] += notional * (
                        1 - self._fee.maker_fee
                    )
                    self.exchange_holdings[pair.quote] += notional * self._fee.maker_fee
            else:
                # agent 是 taker seller：付出 qty，收到 notional - taker_fee
                if trade.seller_id == agent:
                    self.holdings[agent][pair.base] -= trade.quantity
                    self.holdings[agent][pair.quote] += notional * (1 - self._fee.taker_fee)
                    self.exchange_holdings[pair.quote] += notional * self._fee.taker_fee
                # resting buyer 是 maker：支付 exact notional，收到 qty - maker_fee
                if trade.buyer_id in self.holdings:
                    self.holdings[trade.buyer_id][pair.base] += trade.quantity * (
                        1 - self._fee.maker_fee
                    )
                    self.holdings[trade.buyer_id][pair.quote] -= notional
                    self.exchange_holdings[pair.base] += trade.quantity * self._fee.maker_fee

    def _check_terminal(self, agent: AgentId) -> None:
        """检查终止/截断条件。"""
        self.step_count += 1
        if self.step_count >= self.config.env.max_steps:
            for a in self.agents:
                self.truncations[a] = True
            return
        if self.config.env.check_negative_equity:
            equity = self._equity(agent)
            if equity <= 0:
                self.terminations[agent] = True

    def _equity(self, agent: AgentId) -> float:
        """计算 agent 净资产（简化：按最新成交价估算）。"""
        total = 0.0
        for sym, qty in self.holdings[agent].items():
            price = self.prices.get(sym, 0.0)
            total += qty * price
        return total

    def _advance_agent(self) -> None:
        """推进到下一个存活的 agent。"""
        for _ in range(len(self.possible_agents)):
            self._agent_idx = (self._agent_idx + 1) % len(self.possible_agents)
            nxt = self.possible_agents[self._agent_idx]
            if nxt in self.agents:
                self.agent_selection = nxt
                return
        self.agent_selection = ''

    def observation_space(self, agent: AgentId) -> spaces.Space:
        return self.observation_spaces[agent]

    def action_space(self, agent: AgentId) -> spaces.Space:
        return self.action_spaces[agent]

    def state(self) -> np.ndarray:
        """全局状态（CTDE 用）。"""
        raise NotImplementedError

    def render(self) -> None:
        pass
