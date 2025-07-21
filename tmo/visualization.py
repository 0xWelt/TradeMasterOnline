"""TradeMasterOnline 可视化工具模块"""

from datetime import datetime
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .exchange import Exchange
from .typing import AssetType, OrderType


class ExchangeVisualizer:
    """交易所可视化器"""

    def __init__(self):
        """初始化可视化器"""
        self.timeline_data: list[dict[str, Any]] = []
        self.current_step = 0

    def record_snapshot(self, exchange: Exchange, step_name: str, description: str = ''):
        """记录当前时刻的交易所快照"""
        # 获取当前状态
        btc_pair = exchange.get_trading_pair(AssetType.BTC)
        order_book = exchange.get_order_book(AssetType.BTC)
        recent_trades = exchange.get_recent_trades(AssetType.BTC, limit=5)

        # 构建快照数据
        snapshot = {
            'timestamp': datetime.now(),
            'step': self.current_step,
            'step_name': step_name,
            'description': description,
            'price': btc_pair.current_price if btc_pair else 0,
            'buy_orders': [],
            'sell_orders': [],
            'recent_trades': [],
            'total_orders': len(exchange.orders),
            'total_trades': len(exchange.trades),
        }

        # 记录订单簿状态
        if order_book:
            for order in order_book[OrderType.BUY][:5]:  # 前5个买单
                snapshot['buy_orders'].append(
                    {
                        'price': order.price,
                        'quantity': order.remaining_quantity,
                        'user_id': order.user_id,
                        'status': order.status,
                    }
                )

            for order in order_book[OrderType.SELL][:5]:  # 前5个卖单
                snapshot['sell_orders'].append(
                    {
                        'price': order.price,
                        'quantity': order.remaining_quantity,
                        'user_id': order.user_id,
                        'status': order.status,
                    }
                )

        # 记录最近成交
        for trade in recent_trades:
            snapshot['recent_trades'].append(
                {'price': trade.price, 'quantity': trade.quantity, 'timestamp': trade.timestamp}
            )

        self.timeline_data.append(snapshot)
        self.current_step += 1

    def create_visualization(
        self, exchange: Exchange, output_file: str = 'exchange_visualization.html'
    ) -> go.Figure:
        """创建交互式可视化图表"""
        # 创建子图
        fig = make_subplots(
            rows=3,
            cols=2,
            subplot_titles=(
                '价格变化时间轴',
                '订单簿深度',
                '成交量分布',
                '订单状态统计',
                '用户交易活跃度',
                '时间轴控制',
            ),
            specs=[
                [{'secondary_y': False}, {'secondary_y': False}],
                [{'secondary_y': False}, {'type': 'domain'}],
                [{'secondary_y': False}, {'secondary_y': False}],
            ],
            vertical_spacing=0.08,
            horizontal_spacing=0.1,
        )

        # 1. 价格变化时间轴
        if self.timeline_data:
            df_timeline = pd.DataFrame(self.timeline_data)
            fig.add_trace(
                go.Scatter(
                    x=df_timeline['step'],
                    y=df_timeline['price'],
                    mode='lines+markers',
                    name='BTC/USDT 价格',
                    line={'color': '#1f77b4', 'width': 3},
                    marker={'size': 8, 'color': '#1f77b4'},
                    hovertemplate='<b>%{text}</b><br>价格: $%{y:,.2f}<br>步骤: %{x}<extra></extra>',
                    text=df_timeline['step_name'],
                ),
                row=1,
                col=1,
            )

        # 2. 订单簿深度（显示最新状态）
        if self.timeline_data:
            latest_snapshot = self.timeline_data[-1]

            # 买单
            if latest_snapshot['buy_orders']:
                buy_prices = [order['price'] for order in latest_snapshot['buy_orders']]
                buy_quantities = [order['quantity'] for order in latest_snapshot['buy_orders']]
                fig.add_trace(
                    go.Bar(
                        x=buy_prices,
                        y=buy_quantities,
                        name='买单',
                        marker_color='rgba(0, 255, 0, 0.6)',
                        orientation='h',
                        hovertemplate='价格: $%{x:,.2f}<br>数量: %{y} BTC<extra></extra>',
                    ),
                    row=1,
                    col=2,
                )

            # 卖单
            if latest_snapshot['sell_orders']:
                sell_prices = [order['price'] for order in latest_snapshot['sell_orders']]
                sell_quantities = [order['quantity'] for order in latest_snapshot['sell_orders']]
                fig.add_trace(
                    go.Bar(
                        x=sell_prices,
                        y=sell_quantities,
                        name='卖单',
                        marker_color='rgba(255, 0, 0, 0.6)',
                        orientation='h',
                        hovertemplate='价格: $%{x:,.2f}<br>数量: %{y} BTC<extra></extra>',
                    ),
                    row=1,
                    col=2,
                )

        # 3. 成交量分布
        if self.timeline_data:
            all_trades = []
            for snapshot in self.timeline_data:
                all_trades.extend(snapshot['recent_trades'])

            if all_trades:
                df_trades = pd.DataFrame(all_trades)
                fig.add_trace(
                    go.Histogram(
                        x=df_trades['price'],
                        nbinsx=10,
                        name='成交量分布',
                        marker_color='rgba(100, 149, 237, 0.7)',
                        hovertemplate='价格区间: $%{x}<br>成交量: %{y}<extra></extra>',
                    ),
                    row=2,
                    col=1,
                )

        # 4. 订单状态统计
        if self.timeline_data:
            latest_snapshot = self.timeline_data[-1]
            status_counts = {}

            # 统计所有订单状态
            for order in latest_snapshot['buy_orders'] + latest_snapshot['sell_orders']:
                status = order['status']
                status_counts[status] = status_counts.get(status, 0) + 1

            if status_counts:
                fig.add_trace(
                    go.Pie(
                        labels=list(status_counts.keys()),
                        values=list(status_counts.values()),
                        name='订单状态',
                        hole=0.3,
                        hovertemplate='状态: %{label}<br>数量: %{value}<extra></extra>',
                    ),
                    row=2,
                    col=2,
                )

        # 5. 用户交易活跃度
        if self.timeline_data:
            user_activity = {}
            for snapshot in self.timeline_data:
                for order in snapshot['buy_orders'] + snapshot['sell_orders']:
                    user_id = order['user_id']
                    user_activity[user_id] = user_activity.get(user_id, 0) + 1

            if user_activity:
                fig.add_trace(
                    go.Bar(
                        x=list(user_activity.keys()),
                        y=list(user_activity.values()),
                        name='用户活跃度',
                        marker_color='rgba(255, 165, 0, 0.7)',
                        hovertemplate='用户: %{x}<br>订单数: %{y}<extra></extra>',
                    ),
                    row=3,
                    col=1,
                )

        # 6. 时间轴控制（步骤说明）
        if self.timeline_data:
            df_timeline = pd.DataFrame(self.timeline_data)
            fig.add_trace(
                go.Scatter(
                    x=df_timeline['step'],
                    y=[1] * len(df_timeline),  # 固定Y值用于显示
                    mode='markers+text',
                    name='时间轴步骤',
                    marker={'size': 12, 'color': '#ff7f0e'},
                    text=df_timeline['step_name'],
                    textposition='top center',
                    hovertemplate='<b>%{text}</b><br>步骤: %{x}<br>价格: $%{customdata:,.2f}<extra></extra>',
                    customdata=df_timeline['price'],
                ),
                row=3,
                col=2,
            )

        # 更新布局
        fig.update_layout(
            title={
                'text': 'TradeMasterOnline 交易所可视化',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20},
            },
            height=1200,
            showlegend=True,
            template='plotly_white',
            # 添加时间轴滑块
            sliders=[
                {
                    'active': len(self.timeline_data) - 1 if self.timeline_data else 0,
                    'currentvalue': {'prefix': '步骤: ', 'visible': True, 'xanchor': 'right'},
                    'len': 0.9,
                    'x': 0.1,
                    'xanchor': 'left',
                    'y': 0,
                    'yanchor': 'top',
                    'steps': [
                        {
                            'args': [
                                [i],
                                {
                                    'frame': {'duration': 300, 'redraw': True},
                                    'mode': 'immediate',
                                    'transition': {'duration': 300},
                                },
                            ],
                            'label': f'步骤 {i + 1}',
                            'method': 'animate',
                        }
                        for i in range(len(self.timeline_data))
                    ],
                }
            ],
        )

        # 更新坐标轴标签
        fig.update_xaxes(title_text='时间步骤', row=1, col=1)
        fig.update_yaxes(title_text='价格 (USDT)', row=1, col=1)
        fig.update_xaxes(title_text='价格 (USDT)', row=1, col=2)
        fig.update_yaxes(title_text='数量 (BTC)', row=1, col=2)
        fig.update_xaxes(title_text='价格 (USDT)', row=2, col=1)
        fig.update_yaxes(title_text='成交量', row=2, col=1)
        fig.update_xaxes(title_text='用户ID', row=3, col=1)
        fig.update_yaxes(title_text='订单数量', row=3, col=1)
        fig.update_xaxes(title_text='时间步骤', row=3, col=2)
        fig.update_yaxes(title_text='', row=3, col=2, showticklabels=False)

        # 保存图表
        fig.write_html(output_file)

        return fig

    def get_timeline_data(self) -> list[dict[str, Any]]:
        """获取时间轴数据"""
        return self.timeline_data

    def clear_data(self):
        """清空时间轴数据"""
        self.timeline_data = []
        self.current_step = 0
