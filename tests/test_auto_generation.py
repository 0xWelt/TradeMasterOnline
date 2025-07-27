"""测试自动生成的参数防护"""

import pytest

from tmo.constants import TradingPairType
from tmo.typing import Order, OrderType, TradeSettlement, User


class TestAutoGeneration:
    """测试自动生成的参数防护"""

    def test_user_auto_generation_prevention(self):
        """测试用户自动生成的字段防护"""
        # 尝试手动设置id和created_at
        user = User(
            username='testuser',
            email='test@example.com',
            id='manual-id',
            created_at='2023-01-01T00:00:00',
        )

        # 验证自动生成的值被使用，而不是手动设置的值
        assert user.id != 'manual-id'
        assert str(user.created_at.year) != '2023'  # 应该是当前年份
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'

    def test_order_auto_generation_prevention(self):
        """测试订单自动生成的字段防护"""
        user = User(username='testuser', email='test@example.com')

        # 尝试手动设置id和timestamp
        order = Order(
            user=user,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
            id='manual-order-id',
            timestamp='2023-01-01T00:00:00',
            filled_base_amount=999,  # 这个应该被允许设置
        )

        # 验证自动生成的值被使用
        assert order.id != 'manual-order-id'
        assert order.timestamp.year != 2023  # 应该是当前年份
        assert order.filled_base_amount == 999  # 手动设置应该生效
        assert order.user.username == 'testuser'

    def test_trade_auto_generation_prevention(self):
        """测试成交记录自动生成的字段防护"""
        user1 = User(username='buyer', email='buyer@example.com')
        user2 = User(username='seller', email='seller@example.com')

        order1 = Order(
            user=user1,
            order_type=OrderType.BUY,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )
        order2 = Order(
            user=user2,
            order_type=OrderType.SELL,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=1.0,
            price=50000.0,
        )

        # 尝试手动设置timestamp
        trade = TradeSettlement(
            buy_order=order1,
            sell_order=order2,
            trading_pair=TradingPairType.BTC_USDT,
            base_amount=0.5,
            price=50000.0,
            timestamp='2023-01-01T00:00:00',
        )

        # 验证自动生成的值被使用
        assert trade.timestamp.year != 2023  # 应该是当前年份
        assert trade.base_amount == 0.5
        assert trade.price == 50000.0

    def test_extra_fields_rejection(self):
        """测试拒绝额外字段"""
        user = User(username='testuser', email='test@example.com')

        # 尝试设置额外字段应该被拒绝
        with pytest.raises(Exception) as exc_info:
            Order(
                user=user,
                order_type=OrderType.BUY,
                trading_pair=TradingPairType.BTC_USDT,
                base_amount=1.0,
                price=50000.0,
                extra_field='should_be_rejected',
            )

        # 验证错误信息包含extra字段拒绝
        assert 'extra_forbidden' in str(exc_info.value) or 'Extra inputs are not permitted' in str(
            exc_info.value
        )

    def test_frozen_fields_protection(self):
        """测试frozen字段保护"""
        user = User(username='testuser', email='test@example.com')

        # 尝试修改frozen字段应该失败
        original_username = user.username
        with pytest.raises(Exception) as exc_info:
            user.username = 'modified_username'

        assert user.username == original_username
        # 验证错误类型
        assert any(error in str(exc_info.value).lower() for error in ['frozen', 'immutable'])
