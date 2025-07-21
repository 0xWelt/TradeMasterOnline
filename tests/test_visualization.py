"""测试可视化模块"""

import pytest

from tmo import AssetType, Exchange, ExchangeVisualizer, OrderType


class TestExchangeVisualizer:
    """测试交易所可视化器"""

    @pytest.fixture
    def exchange(self) -> Exchange:
        """创建交易所实例"""
        return Exchange()

    @pytest.fixture
    def visualizer(self) -> ExchangeVisualizer:
        """创建可视化器实例"""
        return ExchangeVisualizer()

    def test_visualizer_initialization(self, visualizer: ExchangeVisualizer) -> None:
        """测试可视化器初始化"""
        assert visualizer.timeline_data == []
        assert visualizer.current_step == 0

    def test_record_snapshot(self, exchange: Exchange, visualizer: ExchangeVisualizer) -> None:
        """测试记录快照"""
        # 记录初始快照
        visualizer.record_snapshot(exchange, '初始状态', '测试描述')

        assert len(visualizer.timeline_data) == 1
        assert visualizer.current_step == 1

        snapshot = visualizer.timeline_data[0]
        assert snapshot['step'] == 0
        assert snapshot['step_name'] == '初始状态'
        assert snapshot['description'] == '测试描述'
        assert snapshot['price'] == 50000.0  # 初始价格
        assert snapshot['total_orders'] == 0
        assert snapshot['total_trades'] == 0

    def test_record_snapshot_with_orders(
        self, exchange: Exchange, visualizer: ExchangeVisualizer
    ) -> None:
        """测试记录包含订单的快照"""
        # 下一些订单
        exchange.place_order(
            user_id='user1',
            order_type=OrderType.BUY,
            asset=AssetType.BTC,
            quantity=1.0,
            price=50000.0,
        )

        exchange.place_order(
            user_id='user2',
            order_type=OrderType.SELL,
            asset=AssetType.BTC,
            quantity=0.5,
            price=50000.0,
        )

        # 记录快照
        visualizer.record_snapshot(exchange, '有订单状态')

        assert len(visualizer.timeline_data) == 1
        snapshot = visualizer.timeline_data[0]

        # 检查订单数据
        assert len(snapshot['buy_orders']) > 0 or len(snapshot['sell_orders']) > 0
        assert snapshot['total_orders'] == 2
        assert snapshot['total_trades'] == 1  # 应该有1个成交

    def test_get_timeline_data(self, exchange: Exchange, visualizer: ExchangeVisualizer) -> None:
        """测试获取时间轴数据"""
        visualizer.record_snapshot(exchange, '步骤1')
        visualizer.record_snapshot(exchange, '步骤2')

        data = visualizer.get_timeline_data()
        assert len(data) == 2
        assert data[0]['step_name'] == '步骤1'
        assert data[1]['step_name'] == '步骤2'

    def test_clear_data(self, exchange: Exchange, visualizer: ExchangeVisualizer) -> None:
        """测试清空数据"""
        visualizer.record_snapshot(exchange, '步骤1')
        visualizer.record_snapshot(exchange, '步骤2')

        assert len(visualizer.timeline_data) == 2
        assert visualizer.current_step == 2

        visualizer.clear_data()

        assert len(visualizer.timeline_data) == 0
        assert visualizer.current_step == 0

    def test_create_visualization(self, exchange: Exchange, visualizer: ExchangeVisualizer) -> None:
        """测试创建可视化图表"""
        # 记录一些快照
        visualizer.record_snapshot(exchange, '初始状态')

        exchange.place_order(
            user_id='user1',
            order_type=OrderType.BUY,
            asset=AssetType.BTC,
            quantity=1.0,
            price=50000.0,
        )
        visualizer.record_snapshot(exchange, '下买单')

        # 创建可视化
        fig = visualizer.create_visualization(exchange, 'test_visualization.html')

        # 检查图表对象
        assert fig is not None
        assert hasattr(fig, 'data')
        assert hasattr(fig, 'layout')

    def test_multiple_snapshots(self, exchange: Exchange, visualizer: ExchangeVisualizer) -> None:
        """测试多个快照记录"""
        # 记录多个快照
        for i in range(5):
            visualizer.record_snapshot(exchange, f'步骤{i + 1}')

        assert len(visualizer.timeline_data) == 5
        assert visualizer.current_step == 5

        # 检查步骤编号
        for i, snapshot in enumerate(visualizer.timeline_data):
            assert snapshot['step'] == i
            assert snapshot['step_name'] == f'步骤{i + 1}'
