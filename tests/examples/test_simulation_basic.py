"""基本的交易模拟测试。"""

from tmo.constants import TradingPairType

from examples.trading_simulation import TradingSimulator


def test_simulation_runs_successfully():
    """测试交易模拟能够成功运行。"""
    simulator = TradingSimulator(
        user_count=2,
        trading_rounds=10,
        trading_pairs=[TradingPairType.BTC_USDT],
        seed=42,  # 固定种子确保可重现
    )

    # 运行模拟
    simulator.run_simulation()

    # 验证模拟成功运行
    assert simulator.round_counter == 10
    assert len(simulator.users) == 2
    assert len(simulator.price_history[TradingPairType.BTC_USDT]) == 10

    print('✅ 交易模拟测试通过')
