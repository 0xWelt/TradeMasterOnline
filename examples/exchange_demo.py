"""交易所使用示例 - 带可视化功能"""

from datetime import datetime
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from loguru import logger
from plotly.subplots import make_subplots

from tmo.exchange import Exchange
from tmo.typing import AssetType, OrderType, Trade


# 配置 loguru 只显示 INFO 及以上级别的日志
logger.remove()
logger.add(lambda msg: print(msg, end=''), level='INFO')


class ExchangeVisualizer:
    """交易所可视化器"""

    def __init__(self):
        """初始化可视化器"""
        self.price_history: list[dict[str, Any]] = []
        self.order_history: list[dict[str, Any]] = []
        self.trade_history: list[dict[str, Any]] = []

    def record_price(self, timestamp: datetime, price: float, trading_pair: str):
        """记录价格变化"""
        self.price_history.append(
            {'timestamp': timestamp, 'price': price, 'trading_pair': trading_pair}
        )

    def record_order(self, order: Any, action: str = 'placed'):
        """记录订单"""
        self.order_history.append(
            {
                'timestamp': order.timestamp,
                'order_id': order.id,
                'user_id': order.user_id,
                'order_type': order.order_type.value,
                'quantity': order.quantity,
                'price': order.price,
                'action': action,
                'status': order.status,
            }
        )

    def record_trade(self, trade: Trade):
        """记录成交"""
        self.trade_history.append(
            {
                'timestamp': trade.timestamp,
                'trade_id': trade.id,
                'quantity': trade.quantity,
                'price': trade.price,
                'buy_order_id': trade.buy_order_id,
                'sell_order_id': trade.sell_order_id,
            }
        )

    def create_visualization(
        self, exchange: Exchange, output_file: str = 'exchange_demo.html'
    ) -> go.Figure:
        """创建交互式可视化图表"""
        logger.info('正在生成交互式可视化图表...')

        # 创建子图
        fig = make_subplots(
            rows=3,
            cols=2,
            subplot_titles=(
                '价格变化趋势',
                '订单簿深度',
                '成交量分布',
                '订单状态统计',
                '用户交易活跃度',
                '价格波动分析',
            ),
            specs=[
                [{'secondary_y': False}, {'secondary_y': False}],
                [{'secondary_y': False}, {'type': 'domain'}],
                [{'secondary_y': False}, {'secondary_y': False}],
            ],
            vertical_spacing=0.08,
            horizontal_spacing=0.1,
        )

        # 1. 价格变化趋势
        if self.price_history:
            df_price = pd.DataFrame(self.price_history)
            fig.add_trace(
                go.Scatter(
                    x=df_price['timestamp'],
                    y=df_price['price'],
                    mode='lines+markers',
                    name='BTC/USDT 价格',
                    line={'color': '#1f77b4', 'width': 2},
                    marker={'size': 6},
                ),
                row=1,
                col=1,
            )

        # 2. 订单簿深度
        order_book = exchange.get_order_book(AssetType.BTC)
        if order_book:
            # 买单
            buy_orders = order_book[OrderType.BUY]
            if buy_orders:
                buy_prices = [order.price for order in buy_orders]
                buy_quantities = [order.remaining_quantity for order in buy_orders]
                fig.add_trace(
                    go.Bar(
                        x=buy_prices,
                        y=buy_quantities,
                        name='买单',
                        marker_color='rgba(0, 255, 0, 0.6)',
                        orientation='h',
                    ),
                    row=1,
                    col=2,
                )

            # 卖单
            sell_orders = order_book[OrderType.SELL]
            if sell_orders:
                sell_prices = [order.price for order in sell_orders]
                sell_quantities = [order.remaining_quantity for order in sell_orders]
                fig.add_trace(
                    go.Bar(
                        x=sell_prices,
                        y=sell_quantities,
                        name='卖单',
                        marker_color='rgba(255, 0, 0, 0.6)',
                        orientation='h',
                    ),
                    row=1,
                    col=2,
                )

        # 3. 成交量分布
        if self.trade_history:
            df_trades = pd.DataFrame(self.trade_history)
            fig.add_trace(
                go.Histogram(
                    x=df_trades['price'],
                    nbinsx=10,
                    name='成交量分布',
                    marker_color='rgba(100, 149, 237, 0.7)',
                ),
                row=2,
                col=1,
            )

        # 4. 订单状态统计
        if self.order_history:
            df_orders = pd.DataFrame(self.order_history)
            status_counts = df_orders['status'].value_counts()
            fig.add_trace(
                go.Pie(
                    labels=status_counts.index,
                    values=status_counts.values,
                    name='订单状态',
                    hole=0.3,
                ),
                row=2,
                col=2,
            )

        # 5. 用户交易活跃度
        if self.order_history:
            user_activity = df_orders['user_id'].value_counts()
            fig.add_trace(
                go.Bar(
                    x=user_activity.index,
                    y=user_activity.values,
                    name='用户活跃度',
                    marker_color='rgba(255, 165, 0, 0.7)',
                ),
                row=3,
                col=1,
            )

        # 6. 价格波动分析
        if self.price_history:
            df_price = pd.DataFrame(self.price_history)
            if len(df_price) > 1:
                df_price['price_change'] = df_price['price'].diff()
                fig.add_trace(
                    go.Scatter(
                        x=df_price['timestamp'],
                        y=df_price['price_change'],
                        mode='lines+markers',
                        name='价格变化',
                        line={'color': '#ff7f0e', 'width': 2},
                        marker={'size': 4},
                    ),
                    row=3,
                    col=2,
                )

        # 更新布局
        fig.update_layout(
            title={
                'text': 'TradeMasterOnline 交易所演示 - 交互式可视化',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20},
            },
            height=1200,
            showlegend=True,
            template='plotly_white',
        )

        # 更新坐标轴标签
        fig.update_xaxes(title_text='时间', row=1, col=1)
        fig.update_yaxes(title_text='价格 (USDT)', row=1, col=1)
        fig.update_xaxes(title_text='价格 (USDT)', row=1, col=2)
        fig.update_yaxes(title_text='数量 (BTC)', row=1, col=2)
        fig.update_xaxes(title_text='价格 (USDT)', row=2, col=1)
        fig.update_yaxes(title_text='成交量', row=2, col=1)
        fig.update_xaxes(title_text='用户ID', row=3, col=1)
        fig.update_yaxes(title_text='订单数量', row=3, col=1)
        fig.update_xaxes(title_text='时间', row=3, col=2)
        fig.update_yaxes(title_text='价格变化 (USDT)', row=3, col=2)

        # 保存图表
        fig.write_html(output_file)
        logger.info(f'可视化图表已保存到: {output_file}')

        return fig


def run_exchange_demo():
    """运行交易所演示"""
    logger.info('=== TradeMasterOnline 交易所演示 ===')

    # 创建交易所实例和可视化器
    exchange = Exchange()
    visualizer = ExchangeVisualizer()

    # 记录初始价格
    btc_pair = exchange.get_trading_pair(AssetType.BTC)
    visualizer.record_price(datetime.now(), btc_pair.current_price, 'BTC/USDT')

    # 显示初始状态
    logger.info('1. 初始状态:')
    logger.info(f'   BTC/USDT 当前价格: ${btc_pair.current_price:,.2f}')

    # 用户1下买单
    logger.info('2. 用户1下买单:')
    buy_order1 = exchange.place_order(
        user_id='user1', order_type=OrderType.BUY, asset=AssetType.BTC, quantity=1.0, price=50000.0
    )
    visualizer.record_order(buy_order1)
    logger.info(f'   买单ID: {buy_order1.id}')
    logger.info(f'   数量: {buy_order1.quantity} BTC')
    logger.info(f'   价格: ${buy_order1.price:,.2f}')

    # 用户2下卖单（部分成交）
    logger.info('3. 用户2下卖单:')
    sell_order1 = exchange.place_order(
        user_id='user2', order_type=OrderType.SELL, asset=AssetType.BTC, quantity=0.5, price=50000.0
    )
    visualizer.record_order(sell_order1)
    logger.info(f'   卖单ID: {sell_order1.id}')
    logger.info(f'   数量: {sell_order1.quantity} BTC')
    logger.info(f'   价格: ${sell_order1.price:,.2f}')

    # 记录成交
    recent_trades = exchange.get_recent_trades(AssetType.BTC)
    if recent_trades:
        latest_trade = recent_trades[-1]
        visualizer.record_trade(latest_trade)
        logger.info('4. 成交情况:')
        logger.info(f'   成交ID: {latest_trade.id}')
        logger.info(f'   数量: {latest_trade.quantity} BTC')
        logger.info(f'   价格: ${latest_trade.price:,.2f}')
        logger.info(f'   时间: {latest_trade.timestamp}')

    # 记录价格变化
    btc_pair = exchange.get_trading_pair(AssetType.BTC)
    visualizer.record_price(datetime.now(), btc_pair.current_price, 'BTC/USDT')

    # 显示订单状态
    logger.info('5. 订单状态:')
    buy_order1 = exchange.get_order(buy_order1.id)
    sell_order1 = exchange.get_order(sell_order1.id)

    logger.info(f'   买单状态: {buy_order1.status}')
    logger.info(f'   已成交: {buy_order1.filled_quantity} BTC')
    logger.info(f'   剩余: {buy_order1.remaining_quantity} BTC')

    logger.info(f'   卖单状态: {sell_order1.status}')
    logger.info(f'   已成交: {sell_order1.filled_quantity} BTC')
    logger.info(f'   剩余: {sell_order1.remaining_quantity} BTC')

    # 显示更新后的价格
    logger.info('6. 更新后的价格:')
    logger.info(f'   BTC/USDT 当前价格: ${btc_pair.current_price:,.2f}')

    # 显示订单簿
    logger.info('7. 订单簿:')
    order_book = exchange.get_order_book(AssetType.BTC)
    if order_book:
        logger.info('   买单: ')
        for order in order_book[OrderType.BUY][:3]:  # 显示前3个买单
            logger.info(f'     ${order.price:,.2f} - {order.remaining_quantity} BTC')

        logger.info('   卖单: ')
        for order in order_book[OrderType.SELL][:3]:  # 显示前3个卖单
            logger.info(f'     ${order.price:,.2f} - {order.remaining_quantity} BTC')

    # 用户3下更高价格的买单
    logger.info('8. 用户3下更高价格的买单:')
    buy_order2 = exchange.place_order(
        user_id='user3', order_type=OrderType.BUY, asset=AssetType.BTC, quantity=0.3, price=50100.0
    )
    visualizer.record_order(buy_order2)
    logger.info(f'   买单ID: {buy_order2.id}')
    logger.info(f'   数量: {buy_order2.quantity} BTC')
    logger.info(f'   价格: ${buy_order2.price:,.2f}')

    # 用户4下卖单（与用户3的买单成交）
    logger.info('9. 用户4下卖单:')
    sell_order2 = exchange.place_order(
        user_id='user4', order_type=OrderType.SELL, asset=AssetType.BTC, quantity=0.3, price=50100.0
    )
    visualizer.record_order(sell_order2)
    logger.info(f'   卖单ID: {sell_order2.id}')
    logger.info(f'   数量: {sell_order2.quantity} BTC')
    logger.info(f'   价格: ${sell_order2.price:,.2f}')

    # 记录新的成交
    recent_trades = exchange.get_recent_trades(AssetType.BTC)
    if len(recent_trades) > 1:
        latest_trade = recent_trades[-1]
        visualizer.record_trade(latest_trade)
        logger.info('10. 新的成交:')
        logger.info(f'    成交ID: {latest_trade.id}')
        logger.info(f'    数量: {latest_trade.quantity} BTC')
        logger.info(f'    价格: ${latest_trade.price:,.2f}')

    # 记录最终价格
    btc_pair = exchange.get_trading_pair(AssetType.BTC)
    visualizer.record_price(datetime.now(), btc_pair.current_price, 'BTC/USDT')

    # 用户5取消订单
    logger.info('11. 用户5下买单然后取消:')
    buy_order3 = exchange.place_order(
        user_id='user5', order_type=OrderType.BUY, asset=AssetType.BTC, quantity=0.2, price=50200.0
    )
    visualizer.record_order(buy_order3)
    logger.info(f'   买单ID: {buy_order3.id}')

    # 取消订单
    exchange.cancel_order(buy_order3.id)
    buy_order3 = exchange.get_order(buy_order3.id)
    visualizer.record_order(buy_order3, 'cancelled')
    logger.info(f'   订单已取消，状态: {buy_order3.status}')

    logger.info('=== 演示完成 ===')

    # 生成可视化图表
    logger.info('正在生成可视化图表...')
    visualizer.create_visualization(exchange)

    logger.info('可视化图表已生成完成！')
    logger.info("请在浏览器中打开 'exchange_demo.html' 查看交互式图表")


if __name__ == '__main__':
    run_exchange_demo()
