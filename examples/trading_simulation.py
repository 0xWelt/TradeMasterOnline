"""模拟交易序列生成器

生成随机的合法交易序列，包含用户创建、充值、下单、撤单和成交等动作，
并创建可视化图表展示价格变化。
"""

import random

import plotly.graph_objects as go

from tmo import AssetType, Exchange, OrderType, TradingPairType
from tmo.typing import User


class TradingSimulator:
    """模拟交易序列生成器"""

    def __init__(
        self,
        user_count: int = 3,
        trading_rounds: int = 1000,
        trading_pairs: list[TradingPairType] | None = None,
        seed: int | None = None,
    ):
        """初始化模拟器

        Args:
            user_count: 用户数量，默认3个
            trading_rounds: 交易轮次，默认150轮
            trading_pairs: 交易对列表，默认为所有支持的交易对
            seed: 随机种子，如果为None则使用系统随机源
        """
        if seed is not None:
            random.seed(seed)

        self.user_count = user_count
        self.trading_rounds = trading_rounds
        self.trading_pairs = (
            [pair for pair in trading_pairs]
            if trading_pairs
            else [pair for pair in TradingPairType]
        )

        self.exchange = Exchange()
        self.users: list[User] = []
        self.price_history: dict[str, list[tuple[int, float]]] = {}
        self.round_counter = 0

        # 初始化价格历史
        for pair in self.trading_pairs:
            self.price_history[pair.value] = []

    def create_random_users(self) -> None:
        """创建随机用户"""
        names = [
            'Alice',
            'Bob',
            'Charlie',
            'David',
            'Eva',
            'Frank',
            'Grace',
            'Henry',
            'Ivy',
            'Jack',
        ]
        emails = [f'user{i}@example.com' for i in range(self.user_count)]

        for i in range(min(self.user_count, len(names))):
            user = self.exchange.create_user(username=names[i], email=emails[i])
            self.users.append(user)

        print(f'创建了 {len(self.users)} 个用户')

    def random_deposit(self) -> None:
        """为用户分配等值资产"""
        if not self.users:
            return

        # 每个用户获得等值的USDT、BTC、ETH
        usdt_amount = 50000.0  # 50000 USDT
        btc_amount = 1.0  # 1 BTC ≈ 50000 USDT
        eth_amount = 10.0  # 10 ETH ≈ 50000 USDT (按当前价格)

        for user in self.users:
            # 给每个用户分配固定数量的三种资产
            self.exchange.deposit(user, AssetType.USDT, usdt_amount)
            self.exchange.deposit(user, AssetType.BTC, btc_amount)
            self.exchange.deposit(user, AssetType.ETH, eth_amount)
            print(
                f'用户 {user.username} 充值: {usdt_amount} USDT, {btc_amount} BTC, {eth_amount} ETH'
            )

    def get_current_price(self, trading_pair: TradingPairType) -> float:
        """获取当前价格"""
        return self.exchange.get_market_price(trading_pair)

    def can_place_order(
        self,
        user: User,
        trading_pair: TradingPairType,
        order_type: OrderType,
        quantity: float,
        price: float = 0.0,
    ) -> bool:
        """检查是否可以合法下单"""
        try:
            if order_type in [OrderType.MARKET_BUY, OrderType.BUY]:
                # 检查USDT余额
                usdt_portfolio = self.exchange.get_user_portfolio(user, AssetType.USDT)
                # 对于市价订单，使用当前价格估算
                if price == 0.0:
                    price = self.get_current_price(trading_pair)
                required_amount = quantity * price
                return usdt_portfolio.available_balance >= required_amount
            else:  # SELL or MARKET_SELL
                # 检查资产余额
                asset = trading_pair.base_asset
                asset_portfolio = self.exchange.get_user_portfolio(user, asset)
                return asset_portfolio.available_balance >= quantity
        except ValueError as e:
            print(f'检查订单合法性失败: {e}')
            return False

    def simulate_round(self) -> None:
        """模拟一轮交易 - 简化版本"""
        self.round_counter += 1

        if not self.users:
            return

        # 随机用户行为 - 只下单，不撤单
        for user in random.sample(self.users, k=len(self.users)):
            if random.random() < 0.7:  # 70%概率下单
                self._place_random_order(user)

        # 只在轮次结束时记录最终价格
        for pair in self.trading_pairs:
            engine = self.exchange.trading_pair_engines[pair.value]
            self.price_history[pair.value].append((self.round_counter, engine.current_price))

    def _place_random_order(self, user: User) -> None:
        """随机下单 - 混合使用市价和限价订单"""
        # 混合使用市价和限价订单类型，市价订单概率更高
        if random.random() < 0.7:  # 70% 市价订单
            order_types = [OrderType.MARKET_BUY, OrderType.MARKET_SELL]
        else:  # 30% 限价订单
            order_types = [OrderType.BUY, OrderType.SELL]

        trading_pair = random.choice(self.trading_pairs)
        order_type = random.choice(order_types)

        try:
            # 获取当前市场价格
            current_price = self.get_current_price(trading_pair)
            base_asset = trading_pair.base_asset

            # 根据订单类型计算数量和价格
            if order_type in [OrderType.MARKET_BUY, OrderType.MARKET_SELL]:
                # 市价订单逻辑 - 完全修复版本
                if order_type == OrderType.MARKET_BUY:
                    # 获取USDT可用余额
                    usdt_portfolio = self.exchange.get_user_portfolio(user, AssetType.USDT)
                    max_usdt = usdt_portfolio.available_balance

                    if max_usdt <= 0:
                        return

                    # 确保最小金额，防止零值
                    min_usdt = max(
                        10.0, min(1000.0, max_usdt * 0.1)
                    )  # 确保至少10 USDT，最多1000或10%
                    amount = max(min_usdt, min(max_usdt * 0.8, max_usdt - 1.0))  # 留1.0缓冲

                    # 双重检查确保大于0
                    if amount <= 0:
                        return

                    order = self.exchange.place_order(
                        user=user,
                        order_type=order_type,
                        trading_pair=trading_pair,
                        quote_amount=amount,
                    )
                    execution_msg = ''
                    if order.average_execution_price > 0:
                        execution_msg = f' 实际成交价: ${order.average_execution_price:.2f}'
                    print(
                        f'轮次{self.round_counter}: {user.username} 市价{order_type.value} {amount:.2f} USDT {trading_pair.value}{execution_msg}'
                    )

                else:  # MARKET_SELL
                    # 获取基础资产可用余额
                    asset_portfolio = self.exchange.get_user_portfolio(user, base_asset)
                    max_quantity = asset_portfolio.available_balance

                    if max_quantity <= 0:
                        return

                    # 根据交易对设置最小数量 - 确保不会太小
                    min_quantity = 0.01  # 提高最小值
                    if trading_pair == TradingPairType.BTC_USDT:
                        min_quantity = 0.001  # BTC
                    elif trading_pair == TradingPairType.ETH_USDT:
                        min_quantity = 0.01  # ETH
                    elif trading_pair == TradingPairType.ETH_BTC:
                        min_quantity = 0.001  # ETH/BTC

                    # 计算卖出数量，确保大于最小值且不为零
                    sell_quantity = max(
                        min_quantity, min(max_quantity * 0.8, max_quantity - min_quantity)
                    )

                    # 最终检查确保大于0
                    if sell_quantity <= 0:
                        return

                    order = self.exchange.place_order(
                        user=user,
                        order_type=order_type,
                        trading_pair=trading_pair,
                        base_amount=sell_quantity,
                    )
                    execution_msg = ''
                    if order.average_execution_price > 0:
                        execution_msg = f' 实际成交价: ${order.average_execution_price:.2f}'
                    print(
                        f'轮次{self.round_counter}: {user.username} 市价{order_type.value} {sell_quantity:.6f} {base_asset.value} {trading_pair.value}{execution_msg}'
                    )

            else:  # 限价订单逻辑
                # 限价订单的价格在当前价格±5%范围内波动
                price_fluctuation = random.uniform(-0.05, 0.05)
                target_price = current_price * (1 + price_fluctuation)

                if order_type == OrderType.BUY:
                    # 限价买单价格略低于当前价格
                    target_price = min(target_price, current_price * 0.98)

                    # 获取USDT可用余额
                    usdt_portfolio = self.exchange.get_user_portfolio(user, AssetType.USDT)
                    max_usdt = usdt_portfolio.available_balance

                    if max_usdt <= 0:
                        return

                    # 计算最大可购买数量，确保不为零
                    max_quantity = max_usdt / target_price * 0.8
                    min_quantity = 0.01  # 最小购买量
                    if trading_pair == TradingPairType.BTC_USDT:
                        min_quantity = 0.001
                    elif trading_pair == TradingPairType.ETH_USDT:
                        min_quantity = 0.01

                    if max_quantity < min_quantity:
                        return

                    # 确保数量在有效范围内
                    quantity = max(
                        min_quantity, min(max_quantity * 0.5, max_quantity - min_quantity)
                    )
                    if quantity <= 0:
                        return
                    price = target_price

                    order = self.exchange.place_order(
                        user=user,
                        order_type=order_type,
                        trading_pair=trading_pair,
                        base_amount=quantity,
                        price=price,
                    )
                    execution_msg = ''
                    if order.average_execution_price > 0:
                        execution_msg = f' 实际成交价: ${order.average_execution_price:.2f}'
                    print(
                        f'轮次{self.round_counter}: {user.username} 限价{order_type.value} {quantity:.6f} {base_asset.value}@{price:.2f} {trading_pair.value}{execution_msg}'
                    )

                else:  # OrderType.SELL
                    # 限价卖单价格略高于当前价格
                    target_price = max(target_price, current_price * 1.02)

                    # 获取资产可用余额
                    asset_portfolio = self.exchange.get_user_portfolio(user, base_asset)
                    max_quantity = asset_portfolio.available_balance

                    if max_quantity <= 0:
                        return

                    # 出售最多80%的可用资产，确保不为零
                    max_sell_quantity = max_quantity * 0.8
                    min_quantity = 0.01  # 最小卖出量
                    if trading_pair == TradingPairType.BTC_USDT:
                        min_quantity = 0.001
                    elif trading_pair == TradingPairType.ETH_USDT:
                        min_quantity = 0.01

                    if max_sell_quantity < min_quantity:
                        return

                    # 确保卖出数量在有效范围内
                    quantity = max(
                        min_quantity, min(max_sell_quantity * 0.5, max_sell_quantity - min_quantity)
                    )
                    if quantity <= 0:
                        return
                    price = target_price

                    order = self.exchange.place_order(
                        user=user,
                        order_type=order_type,
                        trading_pair=trading_pair,
                        base_amount=quantity,
                        price=price,
                    )
                    execution_msg = ''
                    if order.average_execution_price > 0:
                        execution_msg = f' 实际成交价: ${order.average_execution_price:.2f}'
                    print(
                        f'轮次{self.round_counter}: {user.username} 限价{order_type.value} {quantity:.6f} {base_asset.value}@{price:.2f} {trading_pair.value}{execution_msg}'
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

    def run_simulation(self) -> None:
        """运行完整模拟"""
        print('=== 开始模拟交易序列 ===')
        print(f'用户数量: {self.user_count} 个')
        print(f'交易轮次: {self.trading_rounds} 轮')
        print(f'交易对: {self.trading_pairs}')

        # 1. 创建用户
        self.create_random_users()

        # 2. 随机充值（仅一次）
        print('\n--- 随机充值阶段 ---')
        self.random_deposit()

        # 3. 模拟交易
        print(f'\n--- 开始{self.trading_rounds}轮交易模拟 ---')
        for i in range(self.trading_rounds):
            print(f'\n第{i + 1}轮交易')
            self.simulate_round()

        print(f'\n=== 模拟完成，共{self.round_counter}轮交易 ===')

    def create_visualization(self, output_file: str = 'trading_simulation.html') -> None:
        """创建价格走势可视化图表"""
        # 使用配置的交易对
        symbols = set(self.trading_pairs)

        # 为每个标的分配颜色
        color_palette = ['#3498db', '#2ecc71', '#e74c3c', '#9b59b6', '#f39c12', '#1abc9c']
        colors = {
            symbol: color_palette[i % len(color_palette)]
            for i, symbol in enumerate(sorted(symbols))
        }

        # 为每个标的创建价格折线图
        figures = {}
        for symbol in colors:
            fig = go.Figure()

            # 添加价格曲线
            if self.price_history.get(symbol):
                x_vals = [p[0] for p in self.price_history[symbol]]
                y_vals = [p[1] for p in self.price_history[symbol]]
                fig.add_trace(
                    go.Scatter(
                        x=x_vals,
                        y=y_vals,
                        mode='lines',
                        name=f'{symbol} 价格',
                        line={'color': colors[symbol], 'width': 3},
                        hovertemplate='轮次: %{x}<br>价格: %{y:.2f}<extra></extra>',
                    )
                )

            # 设置坐标轴标签
            fig.update_xaxes(title_text='轮次')
            fig.update_yaxes(title_text='价格')

            fig.update_layout(
                title=f'{symbol} 价格变化', height=400, showlegend=True, template='plotly_white'
            )

            figures[symbol] = fig

        # 创建简化版HTML
        html_content = self._create_simplified_html(figures, colors)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f'价格图表已保存到: {output_file}')

    def _create_simplified_html(self, figures: dict[str, object], colors: dict[str, str]) -> str:
        """创建交互式HTML内容"""
        # 为每个标的生成图表HTML
        charts_html = {}
        for symbol, fig in figures.items():
            charts_html[symbol] = fig.to_html(include_plotlyjs=False, full_html=False)

        # 生成交易标的按钮HTML (第一个按钮默认激活)
        symbol_buttons_html = ''
        for i, symbol in enumerate(figures.keys()):
            symbol_id = symbol.replace('/', '-')
            symbol_class = symbol.replace('/', '-')
            active_class = ' active' if i == 0 else ''
            symbol_buttons_html += f'<button class="symbol-button {symbol_class}{active_class}" onclick="showChart(\'{symbol_id}\')" data-symbol="{symbol_id}">{symbol}</button>\n            '

        # 生成图表容器HTML (默认隐藏，通过按钮控制显示)
        chart_divs_html = ''
        for i, (symbol, chart_html) in enumerate(charts_html.items()):
            symbol_id = symbol.replace('/', '-')
            # 第一个图表默认显示，其他隐藏
            hidden_class = '' if i == 0 else ' hidden'
            chart_divs_html += f'<div id="{symbol_id}" class="chart-container{hidden_class}">{chart_html}</div>\n            '

        # 简化HTML，只显示价格统计
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TradeMasterOnline - 价格走势</title>
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
        .hidden {{
            display: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h2>选择交易标的</h2>
            {symbol_buttons_html}
        </div>

        <div class="main-content">
            {chart_divs_html}
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
            const activeButton = document.querySelector('[data-symbol="' + symbol + '"]');
            if (activeButton) {{
                activeButton.classList.add('active');
            }}

            // 重新渲染图表以适应容器大小
            const plot = document.getElementById(symbol).querySelector('.js-plotly-plot');
            if (plot) {{
                Plotly.Plots.resize(plot);
            }}
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


def main():
    """主函数"""
    simulator = TradingSimulator(
        user_count=5,
        trading_rounds=500,
        trading_pairs=[TradingPairType.BTC_USDT, TradingPairType.ETH_USDT],
    )

    try:
        # 运行模拟
        simulator.run_simulation()

        # 生成可视化
        simulator.create_visualization('examples/trading_simulation.html')

        # 打印总结
        simulator.print_summary()

    except Exception as e:
        print(f'模拟运行出错: {e}')
        raise


if __name__ == '__main__':
    main()
