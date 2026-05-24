"""随机智能体演示：跑通一个完整 episode 并绘制结果。"""

from __future__ import annotations

import argparse

import matplotlib


matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm

from tmo.env.trading_env import TradingEnv


def run_episode(env: TradingEnv, seed: int = 42) -> dict:
    """用随机动作跑一个 episode，返回历史数据。"""
    rng = np.random.default_rng(seed)
    env.reset(seed=seed)

    n_agents = len(env.possible_agents)
    max_steps = env.config.env.max_steps
    max_iter = max_steps + n_agents

    price_history: list[dict[str, float]] = []
    equity_history: list[dict[str, float]] = []
    trade_count = 0

    for _ in tqdm(range(max_iter), desc='Running episode'):
        agent = env.agent_selection
        if not agent or agent not in env.agents:
            break

        _obs, _reward, termination, truncation, _info = env.last()

        if termination or truncation:
            env.step(None)
        elif rng.random() < 0.1:
            env.step({'asset_id': 0, 'side': 0, 'price': 0.0, 'quantity': 0.0})
        else:
            n_pairs = len(env.config.exchange.pairs)
            asset_id = int(rng.integers(n_pairs))
            side = int(rng.choice([1, 2]))  # BUY or SELL
            pair = env.config.exchange.pairs[asset_id]
            base_price = env.prices.get(pair.base, pair.initial_price)
            price = float(base_price * rng.uniform(0.95, 1.05))
            qty = float(rng.uniform(0.05, 2.0))
            old_price = env.prices.get(pair.base)
            env.step({'asset_id': asset_id, 'side': side, 'price': price, 'quantity': qty})
            if env.prices.get(pair.base) != old_price:
                trade_count += 1

        price_history.append(env.prices.copy())
        equity_history.append({a: env._equity(a) for a in env.possible_agents})

    return {
        'prices': price_history,
        'equity': equity_history,
        'agents': env.possible_agents,
        'pairs': env.config.exchange.pairs,
        'trade_count': trade_count,
    }


def plot_results(history: dict, output_path: str) -> None:
    """绘制每个交易对的价格曲线和仓位价值曲线。"""
    prices = history['prices']
    equity = history['equity']
    agents = history['agents']
    pairs = history['pairs']

    steps = range(len(prices))
    n_pairs = len(pairs)
    n_rows = n_pairs + 1  # 每个交易对一个子图 + equity 子图

    _fig, axes = plt.subplots(n_rows, 1, figsize=(12, 4 * n_rows + 2))
    if n_rows == 1:
        axes = [axes]

    # 每个交易对独立价格曲线
    for idx, pair in enumerate(pairs):
        ax = axes[idx]
        ax.plot(steps, [p.get(pair.base, 0.0) for p in prices], label=pair.base)
        ax.set_title(f'{pair.id} Price Curve')
        ax.set_xlabel('Step')
        ax.set_ylabel(f'Price ({pair.quote})')
        ax.legend()
        ax.grid(True, alpha=0.3)

    # 仓位价值曲线
    ax_equity = axes[-1]
    for agent in agents:
        ax_equity.plot(steps, [e.get(agent, 0.0) for e in equity], label=agent)
    ax_equity.set_title('Agent Equity Curves (USDT)')
    ax_equity.set_xlabel('Step')
    ax_equity.set_ylabel('Equity (USDT)')
    ax_equity.legend()
    ax_equity.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    print(f'Plot saved to {output_path}')


def main() -> None:
    parser = argparse.ArgumentParser(description='Random agents trading demo')
    parser.add_argument(
        '--config',
        '-c',
        default='examples/configs/default.yaml',
        help='Path to config YAML',
    )
    parser.add_argument('--seed', '-s', type=int, default=42, help='Random seed')
    parser.add_argument(
        '--output',
        '-o',
        default='output/trading_results.png',
        help='Output plot path',
    )
    args = parser.parse_args()

    env = TradingEnv.from_config(args.config)
    history = run_episode(env, seed=args.seed)

    # 打印统计
    print('\n=== Episode Statistics ===')
    print(f'Total steps: {len(history["prices"])}')
    print(f'Trade count: {history.get("trade_count", "N/A")}')
    print(f'Final prices: {history["prices"][-1]}')

    initial_equity = history['equity'][0]
    final_equity = history['equity'][-1]
    print('\n--- Agent Equity ---')
    for agent in history['agents']:
        init_eq = initial_equity[agent]
        final_eq = final_equity[agent]
        change = final_eq - init_eq
        print(
            f'{agent}: initial={init_eq:,.2f}, final={final_eq:,.2f}, '
            f'change={change:+,.2f} ({change / init_eq * 100:+.2f}%)'
        )

    plot_results(history, args.output)


if __name__ == '__main__':
    main()
