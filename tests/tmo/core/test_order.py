"""测试 Order 和 Trade 数据模型。"""

from __future__ import annotations

import pytest

from tmo.core.order import Order, Side, Trade


class TestOrder:
    def test_buy_order(self) -> None:
        order = Order(
            order_id='o1',
            agent_id='a1',
            pair_id='BTC/USDT',
            side=Side.BUY,
            price=50000.0,
            quantity=1.0,
        )
        assert order.is_buy()
        assert not order.is_sell()

    def test_sell_order(self) -> None:
        order = Order(
            order_id='o2',
            agent_id='a1',
            pair_id='BTC/USDT',
            side=Side.SELL,
            price=51000.0,
            quantity=0.5,
        )
        assert order.is_sell()
        assert not order.is_buy()

    def test_price_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match='greater than 0'):
            Order(
                order_id='o3',
                agent_id='a1',
                pair_id='BTC/USDT',
                side=Side.BUY,
                price=0.0,
                quantity=1.0,
            )

    def test_quantity_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match='greater than 0'):
            Order(
                order_id='o4',
                agent_id='a1',
                pair_id='BTC/USDT',
                side=Side.BUY,
                price=100.0,
                quantity=-1.0,
            )

    def test_order_is_immutable(self) -> None:
        order = Order(
            order_id='o5',
            agent_id='a1',
            pair_id='BTC/USDT',
            side=Side.BUY,
            price=100.0,
            quantity=1.0,
        )
        with pytest.raises(ValueError, match='frozen'):
            order.price = 200.0  # type: ignore[misc]


class TestTrade:
    def test_trade_notional(self) -> None:
        trade = Trade(
            pair_id='BTC/USDT',
            price=50000.0,
            quantity=1.0,
            buyer_id='a1',
            seller_id='a2',
            buy_order_id='o1',
            sell_order_id='o2',
        )
        assert trade.notional == 50000.0

    def test_buyer_seller_must_differ(self) -> None:
        with pytest.raises(ValueError, match='buyer and seller must be different'):
            Trade(
                pair_id='BTC/USDT',
                price=50000.0,
                quantity=1.0,
                buyer_id='a1',
                seller_id='a1',
                buy_order_id='o1',
                sell_order_id='o2',
            )
