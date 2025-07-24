"""模拟交易序列生成器

生成随机的合法交易序列，包含用户创建、充值、下单、撤单和成交等动作，
并创建可视化图表展示价格变化。
"""

import random
from datetime import datetime

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from tmo import AssetType, Exchange, OrderType
from tmo.typing import User


class TradingSimulator:
    """模拟交易序列生成器"""

    def __init__(self, seed: int = 42):
        """初始化模拟器"""
        random.seed(seed)
        self.exchange = Exchange()
        self.users: list[User] = []
        self.price_history: dict[str, list[tuple[int, float]]] = {}
        self.trade_history: list[dict] = []
        self.order_history: list[dict] = []
        self.round_counter = 0

        # 初始化价格历史
        for symbol in ['BTC/USDT', 'ETH/USDT', 'ETH/BTC']:
            self.price_history[symbol] = []

    def create_random_users(self, count: int = 3) -> None:
        """创建随机用户"""
        names = ['Alice', 'Bob', 'Charlie', 'David', 'Eva', 'Frank']
        emails = [f'user{i}@example.com' for i in range(count)]

        for i in range(min(count, len(names))):
            user = self.exchange.create_user(username=names[i], email=emails[i])
            self.users.append(user)

        print(f'创建了 {len(self.users)} 个用户')

    def random_deposit(self) -> None:
        """随机充值（仅一次）"""
        if not self.users:
            return

        deposit_amounts = {
            AssetType.USDT: (1000, 10000),
            AssetType.BTC: (0.1, 2.0),
            AssetType.ETH: (1.0, 20.0),
        }

        for user in self.users:
            for asset_type, (min_amount, max_amount) in deposit_amounts.items():
                if random.random() < 0.7:  # 70%概率充值
                    amount = random.uniform(min_amount, max_amount)
                    self.exchange.deposit(user, asset_type, amount)
                    print(f'用户 {user.username} 充值 {amount:.4f} {asset_type.value}')

    def get_current_price(self, asset: AssetType) -> float:
        """获取当前价格"""
        if asset == AssetType.BTC:
            return self.exchange.get_market_price(AssetType.BTC)
        elif asset == AssetType.ETH:
            return self.exchange.get_market_price(AssetType.ETH)
        return 1.0

    def generate_price_around_market(self, base_price: float, volatility: float = 0.02) -> float:
        """生成围绕市场价的价格"""
        return base_price * (1 + random.uniform(-volatility, volatility))

    def can_place_order(
        self, user: User, asset: AssetType, order_type: OrderType, quantity: float, price: float
    ) -> bool:
        """检查是否可以合法下单"""
        try:
            if order_type == OrderType.BUY:
                # 检查USDT余额
                usdt_portfolio = self.exchange.get_user_portfolio(user, AssetType.USDT)
                required_amount = quantity * price
                return usdt_portfolio.available_balance >= required_amount
            else:  # SELL
                # 检查资产余额
                asset_portfolio = self.exchange.get_user_portfolio(user, asset)
                return asset_portfolio.available_balance >= quantity
        except ValueError as e:
            print(f'检查订单合法性失败: {e}')
            return False

    def simulate_round(self) -> None:
        """模拟一轮交易"""
        self.round_counter += 1

        if not self.users:
            return

        # 记录当前价格
        for symbol in ['BTC/USDT', 'ETH/USDT', 'ETH/BTC']:
            pair = self.exchange.trading_pairs[symbol]
            self.price_history[symbol].append((self.round_counter, pair.current_price))

        # 记录当前轮产生的成交（通过比较前后状态）
        # 先获取当前成交记录
        all_trades = []
        for symbol in ['BTC/USDT', 'ETH/USDT', 'ETH/BTC']:
            asset = AssetType.BTC if 'BTC' in symbol else AssetType.ETH
            trades = self.exchange.get_recent_trades(asset)
            all_trades.extend(trades)

        # 计算本轮新成交的交易
        # 由于交易立即发生，我们可以认为所有当前交易都是本轮的
        new_trades_count = max(0, len(all_trades) - len(self.trade_history))

        # 添加新交易到历史记录
        for trade in all_trades[-new_trades_count:]:
            asset = trade.asset.value
            symbol = f'{asset}/USDT'
            if (
                asset == 'BTC'
                and trade.sell_order.asset == AssetType.BTC
                and trade.buy_order.asset == AssetType.BTC
            ):
                # BTC/USDT交易对
                pass
            elif (
                asset == 'ETH'
                and trade.sell_order.asset == AssetType.ETH
                and trade.buy_order.asset == AssetType.ETH
            ):
                # 检查是否为ETH/BTC交易对
                eth_btc_trades = [
                    t
                    for t in all_trades
                    if t.asset == AssetType.ETH
                    and any('BTC' in str(o.user.portfolios) for o in [t.buy_order, t.sell_order])
                ]
                if eth_btc_trades:
                    symbol = 'ETH/BTC'

            trade_record = {
                'round': self.round_counter,
                'timestamp': trade.timestamp,
                'asset': asset,
                'symbol': symbol,
                'quantity': trade.quantity,
                'price': trade.price,
                'buyer': trade.buy_order.user.username,
                'seller': trade.sell_order.user.username,
            }
            self.trade_history.append(trade_record)

        # 随机用户行为
        for user in random.sample(self.users, k=len(self.users)):
            action = random.choices(
                ['place_order', 'cancel_order', 'do_nothing'], weights=[0.4, 0.2, 0.4]
            )[0]

            if action == 'place_order':
                self._place_random_order(user)
            elif action == 'cancel_order':
                self._cancel_random_order(user)

    def _place_random_order(self, user: User) -> None:
        """随机下单"""
        assets = [AssetType.BTC, AssetType.ETH]
        order_types = [OrderType.BUY, OrderType.SELL]
        symbols = ['BTC/USDT', 'ETH/USDT', 'ETH/BTC']

        asset = random.choice(assets)
        order_type = random.choice(order_types)
        symbol = random.choice(symbols)

        # 确保资产和交易对匹配
        if asset == AssetType.BTC and 'BTC' not in symbol:
            return
        if asset == AssetType.ETH and 'ETH' not in symbol:
            return

        current_price = self.exchange.get_market_price(asset)
        price = self.generate_price_around_market(current_price)

        # 根据可用余额计算合理的数量范围
        try:
            if order_type == OrderType.BUY:
                # 获取USDT可用余额
                usdt_portfolio = self.exchange.get_user_portfolio(user, AssetType.USDT)
                max_usdt = usdt_portfolio.available_balance

                if max_usdt <= 0:
                    return

                # 计算最大可购买数量，并保留20%缓冲
                max_quantity = max_usdt / price * 0.8
                if max_quantity < 0.001:
                    return

                # 根据资产类型设置合理范围
                if asset == AssetType.BTC:
                    quantity = random.uniform(min(0.001, max_quantity * 0.1), max_quantity)
                else:  # ETH
                    quantity = random.uniform(min(0.01, max_quantity * 0.1), max_quantity)

                # 确保不超过最大可购买数量
                quantity = min(quantity, max_quantity)

            else:  # SELL
                # 获取资产可用余额
                asset_portfolio = self.exchange.get_user_portfolio(user, asset)
                max_quantity = asset_portfolio.available_balance

                if max_quantity <= 0:
                    return

                # 出售最多80%的可用资产
                max_sell_quantity = max_quantity * 0.8
                if max_sell_quantity < 0.001:
                    return

                # 根据资产类型设置合理范围
                if asset == AssetType.BTC:
                    quantity = random.uniform(
                        min(0.001, max_sell_quantity * 0.1), max_sell_quantity
                    )
                else:  # ETH
                    quantity = random.uniform(min(0.01, max_sell_quantity * 0.1), max_sell_quantity)

                # 确保不超过最大可出售数量
                quantity = min(quantity, max_sell_quantity)

        except ValueError as e:
            print(f'计算订单数量失败: {e}')
            return

        # 确保数量为正数
        if quantity <= 0:
            return

        # 验证订单可以成功下单
        if not self.can_place_order(user, asset, order_type, quantity, price):
            return

        try:
            order = self.exchange.place_order(
                user=user, order_type=order_type, asset=asset, quantity=quantity, price=price
            )

            # 记录订单信息
            order_record = {
                'round': self.round_counter,
                'timestamp': datetime.now(),
                'user': user.username,
                'user_id': user.id,
                'order_id': order.id,
                'order_type': order_type.value,
                'asset': asset.value,
                'quantity': quantity,
                'price': price,
                'status': 'placed',
            }
            self.order_history.append(order_record)

            print(
                f'轮次{self.round_counter}: {user.username} 下单 {order_type.value} {quantity:.6f} {asset.value} @ {price:.2f}'
            )

        except ValueError as e:
            print(f'轮次{self.round_counter}: 下单失败 - {e}')

    def _cancel_random_order(self, user: User) -> None:
        """随机撤单"""
        user_orders = [
            order
            for order in self.exchange.orders.values()
            if order.user.id == user.id and order.status == 'pending'
        ]

        if user_orders:
            order_to_cancel = random.choice(user_orders)
            try:
                self.exchange.cancel_order(user, order_to_cancel.id)

                # 更新订单历史中的状态
                for order_record in self.order_history:
                    if order_record['order_id'] == order_to_cancel.id:
                        order_record['status'] = 'cancelled'
                        break

                print(f'轮次{self.round_counter}: {user.username} 撤单 {order_to_cancel.id[:8]}...')
            except ValueError as e:
                print(f'轮次{self.round_counter}: 撤单失败 - {e}')

    def run_simulation(self, rounds: int = 20) -> None:
        """运行完整模拟"""
        print('=== 开始模拟交易序列 ===')

        # 1. 创建用户
        self.create_random_users(random.randint(3, 5))

        # 2. 随机充值（仅一次）
        print('\n--- 随机充值阶段 ---')
        self.random_deposit()

        # 3. 模拟交易
        print(f'\n--- 开始{rounds}轮交易模拟 ---')
        for i in range(rounds):
            print(f'\n第{i + 1}轮交易')
            self.simulate_round()

        print(f'\n=== 模拟完成，共{self.round_counter}轮交易 ===')

    def create_visualization(self, output_file: str = 'trading_simulation.html') -> None:
        """创建交互式交易可视化图表 - 带标的选择按钮"""
        # 自动发现所有交易标的
        symbols = set()
        for trade in self.trade_history:
            symbols.add(trade['symbol'])

        # 为每个标的分配颜色
        color_palette = ['#3498db', '#2ecc71', '#e74c3c', '#9b59b6', '#f39c12', '#1abc9c']
        colors = {
            symbol: color_palette[i % len(color_palette)]
            for i, symbol in enumerate(sorted(symbols))
        }

        # 为每个标的分别计算交易量
        volume_by_symbol = {symbol: {} for symbol in symbols}
        for symbol in symbols:
            for round_num in range(1, self.round_counter + 1):
                volume_by_symbol[symbol][round_num] = 0.0

        # 按标的和轮次统计交易量
        for trade in self.trade_history:
            symbol = trade['symbol']
            round_num = trade['round']
            if round_num <= self.round_counter:
                trade_volume = trade['quantity'] * trade['price']
                volume_by_symbol[symbol][round_num] += trade_volume

        # 为每个标的创建子图
        figures = {}
        for symbol in colors:
            fig = make_subplots(
                rows=2,
                cols=1,
                subplot_titles=(f'{symbol} 价格变化', f'{symbol} 交易量'),
                vertical_spacing=0.1,
                specs=[[{'secondary_y': False}], [{'secondary_y': False}]],
            )

            # 添加价格曲线
            if self.price_history[symbol]:
                x_vals = [p[0] for p in self.price_history[symbol]]
                y_vals = [p[1] for p in self.price_history[symbol]]
                fig.add_trace(
                    go.Scatter(
                        x=x_vals,
                        y=y_vals,
                        mode='lines+markers',
                        name=f'{symbol} 价格',
                        line={'color': colors[symbol], 'width': 3},
                        marker={'size': 6},
                        hovertemplate='轮次: %{x}<br>价格: %{y:.2f}<extra></extra>',
                    ),
                    row=1,
                    col=1,
                )

            # 添加交易量柱状图
            volumes = list(volume_by_symbol[symbol].values())
            rounds = list(volume_by_symbol[symbol].keys())
            fig.add_trace(
                go.Bar(
                    x=rounds,
                    y=volumes,
                    name=f'{symbol} 交易量',
                    marker_color=colors[symbol],
                    opacity=0.7,
                    hovertemplate='轮次: %{x}<br>交易量: %{y:.2f}<extra></extra>',
                ),
                row=2,
                col=1,
            )

            # 设置坐标轴标签
            fig.update_xaxes(title_text='轮次', row=1, col=1)
            fig.update_yaxes(title_text='价格', row=1, col=1)
            fig.update_xaxes(title_text='轮次', row=2, col=1)
            fig.update_yaxes(title_text='交易量', row=2, col=1)

            fig.update_layout(
                title=f'{symbol} 交易分析', height=600, showlegend=True, template='plotly_white'
            )

            figures[symbol] = fig

        # 创建交互式HTML
        html_content = self._create_interactive_html(figures, colors)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f'交互式可视化图表已保存到: {output_file}')

    def _create_interactive_html(self, figures: dict[str, object], colors: dict[str, str]) -> str:
        """创建交互式HTML内容"""
        # 为每个标的生成图表HTML
        charts_html = {}
        for symbol, fig in figures.items():
            charts_html[symbol] = fig.to_html(include_plotlyjs=False, full_html=False)

        total_trades = len(self.trade_history)
        total_orders = len(self.order_history)

        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TradeMasterOnline - 交互式交易模拟</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }}
        .container {{
            display: flex;
            height: 100vh;
        }}
        .sidebar {{
            width: 250px;
            background-color: #2c3e50;
            padding: 20px;
            box-shadow: 2px 0 5px rgba(0,0,0,0.1);
        }}
        .main-content {{
            flex: 1;
            padding: 20px;
            overflow-y: auto;
        }}
        .sidebar h2 {{
            color: #ecf0f1;
            margin-bottom: 20px;
            font-size: 18px;
        }}
        .symbol-button {{
            display: block;
            width: 100%;
            padding: 12px;
            margin-bottom: 10px;
            background-color: #34495e;
            color: #ecf0f1;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: background-color 0.3s;
        }}
        .symbol-button:hover {{
            background-color: #3498db;
        }}
        .symbol-button.active {{
            background-color: #3498db;
            font-weight: bold;
        }}
        .symbol-button.BTC-USDT {{ border-left: 4px solid #3498db; }}
        .symbol-button.ETH-USDT {{ border-left: 4px solid #2ecc71; }}
        .symbol-button.ETH-BTC {{ border-left: 4px solid #e74c3c; }}
        .chart-container {{
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
        }}
        .stats {{
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
        }}
        .stats h3 {{
            margin-top: 0;
            color: #2c3e50;
        }}
        .stat-item {{
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px solid #eee;
        }}
        .hidden {{
            display: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h2>选择交易标的</h2>
            <button class="symbol-button BTC-USDT active" onclick="showChart('BTC/USDT')">BTC/USDT</button>
            <button class="symbol-button ETH-USDT" onclick="showChart('ETH/USDT')">ETH/USDT</button>
            <button class="symbol-button ETH-BTC" onclick="showChart('ETH/BTC')">ETH/BTC</button>

            <div class="stats">
                <h3>交易统计</h3>
                <div class="stat-item">
                    <span>总轮次:</span>
                    <span>{self.round_counter}</span>
                </div>
                <div class="stat-item">
                    <span>总订单:</span>
                    <span>{total_orders}</span>
                </div>
                <div class="stat-item">
                    <span>总成交:</span>
                    <span>{total_trades}</span>
                </div>
            </div>
        </div>

        <div class="main-content">
            <div id="BTC/USDT" class="chart-container">
                {charts_html['BTC/USDT']}
            </div>

            <div id="ETH/USDT" class="chart-container hidden">
                {charts_html['ETH/USDT']}
            </div>

            <div id="ETH/BTC" class="chart-container hidden">
                {charts_html['ETH/BTC']}
            </div>
        </div>
    </div>

    <script>
        function showChart(symbol) {{
            // 隐藏所有图表
            const charts = document.querySelectorAll('.chart-container');
            charts.forEach(chart => chart.classList.add('hidden'));

            // 移除所有按钮的active类
            const buttons = document.querySelectorAll('.symbol-button');
            buttons.forEach(button => button.classList.remove('active'));

            // 显示选中的图表
            document.getElementById(symbol).classList.remove('hidden');

            // 激活对应的按钮
            const activeButton = document.querySelector(`[onclick="showChart('{symbol}')"]');
            activeButton.classList.add('active');

            // 重新渲染图表以适应容器大小
            Plotly.Plots.resize(document.getElementById(symbol).querySelector('.js-plotly-plot'));
        }}

        // 初始化时调整大小
        window.addEventListener('load', function() {{
            setTimeout(() => {{
                const charts = document.querySelectorAll('.js-plotly-plot');
                charts.forEach(chart => Plotly.Plots.resize(chart));
            }}, 100);
        }});

        // 窗口大小改变时重新调整
        window.addEventListener('resize', function() {{
            const activeChart = document.querySelector('.chart-container:not(.hidden) .js-plotly-plot');
            if (activeChart) {{
                Plotly.Plots.resize(activeChart);
            }}
        }});
    </script>
</body>
</html>
        """
        return html_content

    def print_orders_list(self) -> None:
        """打印所有订单列表"""
        print('\n=== 订单历史 ===')
        if not self.order_history:
            print('暂无订单记录')
            return

        print(
            f'{"轮次":<6} {"时间":<20} {"用户":<10} {"订单ID":<12} {"类型":<6} {"资产":<6} {"数量":<12} {"价格":<10} {"状态":<8}'
        )
        print('-' * 95)

        for order in self.order_history:
            timestamp_str = order['timestamp'].strftime('%H:%M:%S')
            print(
                f'{order["round"]:<6} {timestamp_str:<20} {order["user"]:<10} {order["order_id"][:10]:<12} '
                f'{order["order_type"]:<6} {order["asset"]:<6} {order["quantity"]:<12.6f} '
                f'{order["price"]:<10.2f} {order["status"]:<8}'
            )

    def print_summary(self) -> None:
        """打印模拟总结"""
        print('\n=== 模拟总结 ===')

        # 用户持仓
        for user in self.users:
            print(f'\n用户: {user.username}')
            for asset_type, portfolio in user.portfolios.items():
                if portfolio.total_balance > 0:
                    print(
                        f'  {asset_type.value}: 可用 {portfolio.available_balance:.4f}, '
                        f'锁定 {portfolio.locked_balance:.4f}, 总计 {portfolio.total_balance:.4f}'
                    )

        # 订单统计
        total_orders = len(self.order_history)
        buy_orders = len([o for o in self.order_history if o['order_type'] == 'buy'])
        sell_orders = len([o for o in self.order_history if o['order_type'] == 'sell'])
        active_orders = len([o for o in self.exchange.orders.values() if o.status == 'pending'])

        print('\n订单统计:')
        print(f'  总订单数: {total_orders}')
        print(f'  买单: {buy_orders}')
        print(f'  卖单: {sell_orders}')
        print(f'  活跃订单: {active_orders}')

        # 交易统计
        total_trades = 0
        for symbol in ['BTC/USDT', 'ETH/USDT', 'ETH/BTC']:
            trades = self.exchange.get_recent_trades(
                AssetType.BTC if 'BTC' in symbol else AssetType.ETH
            )
            print(f'\n{symbol}: {len(trades)} 笔成交')
            total_trades += len(trades)

        print(f'\n总成交: {total_trades} 笔')


def main():
    """主函数"""
    simulator = TradingSimulator(seed=123)

    try:
        # 运行模拟
        simulator.run_simulation(rounds=150)

        # 生成可视化
        simulator.create_visualization('examples/trading_simulation.html')

        # 打印订单列表
        simulator.print_orders_list()

        # 打印总结
        simulator.print_summary()

    except Exception as e:
        print(f'模拟运行出错: {e}')
        raise


if __name__ == '__main__':
    main()
