"""模拟交易序列生成器。

该模块提供了完整的交易模拟功能，包括用户创建、随机订单生成、
智能撤单逻辑和价格历史记录。支持多交易对、多用户的复杂交易场景模拟。

主要功能：
    - 创建测试用户并分配初始资金
    - 按轮次模拟交易活动
    - 智能订单撤销策略
    - 实时价格记录和可视化
    - 交易结果汇总分析

示例：
    simulator = TradingSimulator(user_count=5, trading_rounds=1000)
    simulator.run_simulation()
    simulator.create_visualization('output.html')
"""

import random

import plotly.graph_objects as go

from tmo import AssetType, Exchange, OrderStatus, OrderType, TradingPairType, User


class TradingSimulator:
    """交易模拟器核心类。

    提供完整的交易模拟环境，支持多用户、多交易对的复杂交易场景。
    每轮模拟中，用户以相等概率进行下单或撤单操作，避免订单积压。

    Attributes:
        user_count: 模拟用户数量，默认为3个。
        trading_rounds: 总交易轮次，默认为1000轮。
        trading_pairs: 交易对列表，支持多种加密货币交易对。
        exchange: 交易所实例，提供核心的交易功能。
        users: 用户列表，包含所有参与模拟的用户。
        price_history: 价格历史记录，按交易对分组存储。
        round_counter: 当前轮次计数器。
    """

    def __init__(
        self,
        user_count: int = 3,
        trading_rounds: int = 1000,
        trading_pairs: list[TradingPairType] | None = None,
        seed: int | None = None,
    ):
        if seed is not None:
            random.seed(seed)

        self.user_count = user_count
        self.trading_rounds = trading_rounds
        self.trading_pairs = trading_pairs or list(TradingPairType)
        self.exchange = Exchange()
        self.users: list[User] = []
        self.price_history: dict[str, list[tuple[int, float]]] = {}
        self.round_counter = 0

        for pair in self.trading_pairs:
            self.price_history[pair] = []

    def create_random_users(self) -> None:
        """创建随机测试用户。

        根据指定的用户数量创建测试用户，并初始化用户列表。
        用户名从预定义列表中选取，确保唯一性。

        Example:
            创建了 5 个用户
        """
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

        for i in range(min(self.user_count, len(names))):
            user = self.exchange.create_user(username=names[i], email=f'user{i}@example.com')
            self.users.append(user)

        print(f'创建了 {len(self.users)} 个用户')

    def random_deposit(self) -> None:
        """为用户充值初始资金。

        为每个用户按照BTC的标准价值比例充值所有支持资产的等值数量。
        每个用户获得每种资产的初始价值为1个BTC等值的数量。

        充值策略：
            - 每种资产的充值数量 = 1 BTC的价值 / 该资产的初始价值
        """
        if not self.users:
            return

        # 1个BTC的标准价值
        btc_base_value = AssetType.BTC.initial_value

        for user in self.users:
            for asset in AssetType:
                # 计算等值数量
                amount = btc_base_value / asset.initial_value
                user.deposit(asset, amount)

            print(f'用户 {user.username} 充值完成:')
            for asset in AssetType:
                balance = user.get_total_balance(asset)
                print(f'  {asset.value}: {balance:.6f}')

    def get_current_price(self, trading_pair: TradingPairType) -> float:
        return self.exchange.get_trading_pair(trading_pair).get_current_price()

    def can_place_order(
        self,
        user: User,
        trading_pair: TradingPairType,
        order_type: OrderType,
        quantity: float,
        price: float = 0.0,
    ) -> bool:
        try:
            if price == 0.0:
                price = self.get_current_price(trading_pair)

            if order_type in [OrderType.MARKET_BUY, OrderType.BUY]:
                return user.get_available_balance(AssetType.USDT) >= quantity * price
            else:
                return user.get_available_balance(trading_pair.base_asset) >= quantity
        except ValueError as e:
            print(f'检查订单合法性失败: {e}')
            return False

    def simulate_round(self) -> None:
        """执行一轮交易模拟。

        每轮中，每个用户先随机选择交易对，然后检查该交易对是否有订单。
        如果没有订单则一定下单，如果有订单则随机决定下单或撤单。
        这样可以避免"无订单可撤销"的情况。
        """
        self.round_counter += 1
        if not self.users:
            return

        for user in random.sample(self.users, k=len(self.users)):
            trading_pair = random.choice(self.trading_pairs)
            user_orders = self._get_user_orders_in_pair(user, trading_pair)

            if not user_orders:
                # 如果该用户在当前交易对没有订单，一定下单
                self._place_random_order_in_pair(user, trading_pair)
            else:
                # 如果有订单，随机决定下单或撤单
                if random.random() < 0.5:
                    self._place_random_order_in_pair(user, trading_pair)
                else:
                    self._cancel_random_order_in_pair(user, trading_pair)

        for pair in self.trading_pairs:
            price = self.exchange.get_trading_pair(pair).current_price
            self.price_history[pair].append((self.round_counter, price))

    def _get_user_orders_in_pair(self, user: User, trading_pair: TradingPairType) -> list:
        """获取用户在指定交易对的所有活跃订单。

        遍历用户的活跃订单字典结构，收集指定交易对的所有待成交和部分成交订单。

        Args:
            user: 用户对象
            trading_pair: 交易对

        Returns:
            list: 用户在该交易对的活跃订单列表

        Example:
            >>> orders = self._get_user_orders_in_pair(user, TradingPairType.BTC_USDT)
            >>> print(len(orders))  # 输出: 3
        """
        orders = []
        if trading_pair in user.active_orders:
            for order_type in user.active_orders[trading_pair]:
                orders.extend(
                    [
                        order
                        for order in user.active_orders[trading_pair][order_type]
                        if order.status in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]
                    ]
                )
        return orders

    def _place_random_order_in_pair(self, user: User, trading_pair: TradingPairType) -> None:
        """在指定交易对随机下单。

        Args:
            user: 用户对象
            trading_pair: 交易对
        """
        # 根据用户资产情况智能选择订单类型，避免USDT过度锁定
        usdt_balance = user.get_available_balance(AssetType.USDT)
        base_asset = trading_pair.base_asset
        base_balance = user.get_available_balance(base_asset)

        # 计算买卖倾向，根据资产比例调整
        total_usdt_value = usdt_balance + base_balance * self.get_current_price(trading_pair)

        # 如果USDT占比过高，增加卖单概率
        if usdt_balance > total_usdt_value * 0.8 and base_balance > 0:
            order_type = OrderType.SELL if random.random() < 0.9 else OrderType.BUY
        # 如果基础资产占比过高，增加买单概率
        elif base_balance > total_usdt_value * 0.8 and usdt_balance > 0:
            order_type = OrderType.BUY if random.random() < 0.9 else OrderType.SELL
        else:
            # 平衡状态，随机选择
            order_type = OrderType.BUY if random.random() < 0.5 else OrderType.SELL

        try:
            current_price = self.get_current_price(trading_pair)
            base_asset = trading_pair.base_asset

            # 根据资产可用性和订单类型决定使用市价还是限价订单
            use_market = random.random() < 0.3  # 30%概率使用市价单

            if use_market:
                if order_type == OrderType.BUY:
                    # 市价买单需要USDT
                    if user.get_available_balance(AssetType.USDT) > 0:
                        self._place_market_order(
                            user, trading_pair, OrderType.MARKET_BUY, base_asset
                        )
                else:  # SELL
                    # 市价卖单需要基础资产
                    if user.get_available_balance(base_asset) > 0:
                        self._place_market_order(
                            user, trading_pair, OrderType.MARKET_SELL, base_asset
                        )
            else:
                if order_type == OrderType.BUY:
                    # 限价买单需要USDT
                    if user.get_available_balance(AssetType.USDT) > 0:
                        self._place_limit_order(
                            user, trading_pair, OrderType.BUY, base_asset, current_price
                        )
                else:  # SELL
                    # 限价卖单需要基础资产
                    if user.get_available_balance(base_asset) > 0:
                        self._place_limit_order(
                            user, trading_pair, OrderType.SELL, base_asset, current_price
                        )

        except ValueError as e:
            print(f'轮次{self.round_counter}: 下单失败 - {e}')

    def _place_market_order(
        self,
        user: User,
        trading_pair: TradingPairType,
        order_type: OrderType,
        base_asset: AssetType,
    ) -> None:
        if order_type == OrderType.MARKET_BUY:
            max_usdt = user.get_available_balance(AssetType.USDT)
            if max_usdt <= 0:
                return
            amount = random.uniform(10.0, max_usdt)
            if amount <= 0:
                return
            self.exchange.get_trading_pair(trading_pair).place_order(
                user=user, order_type=order_type, quote_amount=amount
            )
            print(
                f'轮次{self.round_counter}: {user.username} 市价{order_type.value} {amount:.2f} USDT {trading_pair.value}'
            )
        else:
            max_quantity = user.get_available_balance(base_asset)
            if max_quantity <= 0:
                return
            quantity = random.uniform(0.001, max_quantity)
            if quantity <= 0:
                return
            self.exchange.get_trading_pair(trading_pair).place_order(
                user=user, order_type=order_type, base_amount=quantity
            )
            print(
                f'轮次{self.round_counter}: {user.username} 市价{order_type.value} {quantity:.6f} {base_asset.value} {trading_pair.value}'
            )

    def _place_limit_order(
        self,
        user: User,
        trading_pair: TradingPairType,
        order_type: OrderType,
        base_asset: AssetType,
        current_price: float,
    ) -> None:
        target_price = current_price * (1 + random.uniform(-0.005, 0.005))

        if order_type == OrderType.BUY:
            max_usdt = user.get_available_balance(AssetType.USDT)
            if max_usdt <= 0:
                return
            max_quantity = max_usdt / target_price
            quantity = random.uniform(0.001, max_quantity)
            if quantity <= 0:
                return
            self.exchange.get_trading_pair(trading_pair).place_order(
                user=user, order_type=order_type, base_amount=quantity, price=target_price
            )
            print(
                f'轮次{self.round_counter}: {user.username} 限价{order_type.value} {quantity:.6f} {base_asset.value}@{target_price:.2f} {trading_pair.value}'
            )
        else:
            max_quantity = user.get_available_balance(base_asset)
            if max_quantity <= 0:
                return
            quantity = random.uniform(0.001, max_quantity)
            if quantity <= 0:
                return
            self.exchange.get_trading_pair(trading_pair).place_order(
                user=user, order_type=order_type, base_amount=quantity, price=target_price
            )
            print(
                f'轮次{self.round_counter}: {user.username} 限价{order_type.value} {quantity:.6f} {base_asset.value}@{target_price:.2f} {trading_pair.value}'
            )

    def _cancel_random_order_in_pair(self, user: User, trading_pair: TradingPairType) -> None:
        """在指定交易对撤销订单。

        随机撤销用户在该交易对的任意一个活跃订单，避免USDT长期锁定。
        直接从用户的活跃订单列表中获取订单进行撤销。

        Args:
            user: 用户对象
            trading_pair: 交易对
        """
        engine = self.exchange.get_trading_pair(trading_pair)

        # 直接从用户的活跃订单中获取
        user_orders = self._get_user_orders_in_pair(user, trading_pair)

        if user_orders:
            # 随机选择一个订单撤销
            order = random.choice(user_orders)
            try:
                engine.cancel_order(order, user)
                order_type_name = '市价' if 'market' in order.order_type.value else '限价'
                print(
                    f'轮次{self.round_counter}: {user.username} 在 {trading_pair.value} 撤销{order_type_name}订单成功'
                )
            except ValueError as e:
                print(f'轮次{self.round_counter}: 撤销订单失败 - {e}')

    def run_simulation(self) -> None:
        print('=== 开始模拟交易序列 ===')
        print(f'用户数量: {self.user_count} 个')
        print(f'交易轮次: {self.trading_rounds} 轮')
        print(f'交易对: {self.trading_pairs}')

        self.create_random_users()
        self.random_deposit()

        for i in range(self.trading_rounds):
            print(f'\n第{i + 1}轮交易')
            self.simulate_round()

        print(f'\n=== 模拟完成，共{self.round_counter}轮交易 ===')

    def create_visualization(self, output_file: str = 'trading_simulation.html') -> None:
        colors = {
            pair: ['#3498db', '#2ecc71', '#e74c3c'][i % 3]
            for i, pair in enumerate(self.trading_pairs)
        }

        figures = {}
        for pair in self.trading_pairs:
            fig = go.Figure()
            if self.price_history.get(pair):
                x_vals = [p[0] for p in self.price_history[pair]]
                y_vals = [p[1] for p in self.price_history[pair]]
                fig.add_trace(
                    go.Scatter(
                        x=x_vals,
                        y=y_vals,
                        mode='lines',
                        name=f'{pair.value} 价格',
                        line={'color': colors[pair], 'width': 3},
                        hovertemplate='轮次: %{x}<br>价格: %{y:.2f}<extra></extra>',
                    )
                )
                fig.update_xaxes(title_text='轮次')
                fig.update_yaxes(title_text='价格')
                fig.update_layout(
                    title=f'{pair.value} 价格变化', height=400, template='plotly_white'
                )
                figures[pair] = fig

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(self._create_simplified_html(figures, colors))

        print(f'价格图表已保存到: {output_file}')

    def _create_simplified_html(self, figures: dict, colors: dict) -> str:
        charts_html = {
            pair: fig.to_html(include_plotlyjs=False, full_html=False)
            for pair, fig in figures.items()
        }

        buttons = []
        divs = []
        for i, pair in enumerate(figures.keys()):
            pair_id = str(pair).replace('/', '-')
            active = '' if i else ' active'
            hidden = '' if i else ' hidden'
            buttons.append(
                f'<button class="symbol-button{active}" onclick="showChart(\'{pair_id}\')">{pair.value}</button>'
            )
            divs.append(
                f'<div id="{pair_id}" class="chart-container{hidden}">{charts_html[pair]}</div>'
            )

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>TradeMasterOnline - 价格走势</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{ font-family: system-ui, sans-serif; margin: 0; background: #f5f5f5; }}
        .container {{ display: flex; height: 100vh; }}
        .sidebar {{ width: 200px; background: #2c3e50; padding: 20px; }}
        .main {{ flex: 1; padding: 20px; }}
        .symbol-button {{ width: 100%; padding: 10px; margin: 5px 0; background: #34495e; color: white; border: none; border-radius: 4px; cursor: pointer; }}
        .symbol-button.active {{ background: #3498db; }}
        .chart-container {{ background: white; border-radius: 8px; padding: 20px; margin: 10px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .hidden {{ display: none; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">{''.join(buttons)}</div>
        <div class="main">{''.join(divs)}</div>
    </div>
    <script>
        function showChart(symbol) {{
            document.querySelectorAll('.chart-container').forEach(el => el.classList.add('hidden'));
            document.querySelectorAll('.symbol-button').forEach(el => el.classList.remove('active'));
            document.getElementById(symbol).classList.remove('hidden');
            event.target.classList.add('active');
            Plotly.Plots.resize(document.getElementById(symbol).querySelector('.js-plotly-plot'));
        }}
    </script>
</body>
</html>"""

    def print_summary(self) -> None:
        print('\n=== 模拟总结 ===')

        # 打印每个交易对的当前挂单
        print('\n=== 交易对挂单情况 ===')
        for pair in self.trading_pairs:
            engine = self.exchange.get_trading_pair(pair)
            order_book = engine.get_order_book()

            print(f'\n{pair.value}:')
            print('  买单:')
            for bid in order_book.bids[:5]:  # 前5个买单
                print(f'    价格: {bid.price:.2f}, 数量: {bid.quantity:.6f}')

            print('  卖单:')
            for ask in order_book.asks[:5]:  # 前5个卖单
                print(f'    价格: {ask.price:.2f}, 数量: {ask.quantity:.6f}')

            print(f'  当前价格: {engine.get_current_price():.2f}')

        print('\n=== 用户资产情况 ===')
        for user in self.users:
            print(f'\n用户: {user.username}')
            for asset in AssetType:
                total = user.get_total_balance(asset)
                if total > 0:
                    available = user.get_available_balance(asset)
                    locked = user.get_locked_balance(asset)
                    print(
                        f'  {asset.value}: 可用 {available:.4f}, 锁定 {locked:.4f}, 总计 {total:.4f}'
                    )

            # 添加活跃订单详情调试
            print('  活跃订单详情:')
            for pair in self.trading_pairs:
                if pair in user.active_orders:
                    total_orders = 0
                    for order_type, orders in user.active_orders[pair].items():
                        active_orders = [
                            o for o in orders if o.status in ['pending', 'partially_filled']
                        ]
                        if active_orders:
                            total_orders += len(active_orders)
                            print(
                                f'    {pair.value} {order_type.value}: {len(active_orders)}个订单'
                            )
                            for order in active_orders[:3]:  # 显示前3个
                                print(
                                    f'      状态: {order.status}, 剩余: {order.remaining_base_amount:.6f}, 价格: {order.price}'
                                )
                    if total_orders == 0:
                        print(f'    {pair.value}: 无活跃订单')
                else:
                    print(f'    {pair.value}: 无活跃订单')


def main():
    simulator = TradingSimulator(
        user_count=5,
        trading_rounds=1000,
        trading_pairs=[TradingPairType.BTC_USDT, TradingPairType.ETH_USDT],
    )

    try:
        simulator.run_simulation()
        simulator.create_visualization('examples/trading_simulation.html')
        simulator.print_summary()
    except Exception as e:
        print(f'模拟运行出错: {e}')
        raise


if __name__ == '__main__':
    main()
