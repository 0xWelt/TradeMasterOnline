"""模拟交易序列生成器。

提供完整的交易模拟环境，支持多用户、多交易对的复杂交易场景模拟。
实现智能的订单生成、撤销策略和实时价格记录，可用于交易策略验证和系统测试。

主要功能：
    - 创建测试用户并分配初始资金
    - 按轮次模拟交易活动
    - 智能订单撤销策略
    - 实时价格记录和可视化
    - 交易结果汇总分析

示例：
    >>> simulator = TradingSimulator(user_count=5, trading_rounds=1000)
    >>> simulator.run_simulation()
    >>> simulator.create_visualization('output.html')

该模拟器采用交易对优先的轮询策略，确保每个用户在每个交易对都有订单可撤销，
避免"无订单可撤销"的情况发生。
"""

import random

import plotly.graph_objects as go

from tmo import AssetType, Exchange, OrderStatus, OrderType, TradingPairType, User
from tmo.trading_pair import TradingPairEngine


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

        Raises:
            ValueError: 如果没有用户存在，则跳过充值操作。
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
            user: 用户对象，包含用户的订单信息。
            trading_pair: 交易对，指定要查询的交易市场。

        Returns:
            list: 用户在该交易对的活跃订单列表，只包含状态为待成交或部分成交的订单。

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

        根据用户资产情况智能选择订单类型和价格，避免USDT过度锁定。
        使用统一的订单放置方法减少代码重复。

        Args:
            user: 用户对象
            trading_pair: 交易对
        """
        order_type = self._determine_order_type(user, trading_pair)
        if not order_type:
            return

        current_price = self.get_current_price(trading_pair)
        is_market = random.random() < 0.3  # 30%概率使用市价单

        # 强制终止程序的错误检查
        if not is_market and order_type in [OrderType.BUY, OrderType.SELL]:
            assert current_price is not None, '限价订单必须有价格'

        self._place_order(user, trading_pair, order_type, current_price, is_market)

    def _determine_order_type(self, user: User, trading_pair: TradingPairType) -> OrderType | None:
        """根据用户资产情况确定订单类型。

        Args:
            user: 用户对象
            trading_pair: 交易对

        Returns:
            OrderType | None: 确定的订单类型，如果无法下单则返回None
        """
        usdt_balance = user.get_available_balance(AssetType.USDT)
        base_asset = trading_pair.base_asset
        base_balance = user.get_available_balance(base_asset)

        # 检查是否有足够的资产进行任何操作
        if usdt_balance <= 0 and base_balance <= 0:
            return None

        # 计算资产总值
        total_value = usdt_balance + base_balance * self.get_current_price(trading_pair)

        # 根据资产比例智能选择买卖方向
        if usdt_balance > total_value * 0.8 and base_balance > 0:
            # USDT过多，应该买入资产
            return OrderType.BUY if random.random() < 0.9 else OrderType.SELL
        elif base_balance > total_value * 0.8 and usdt_balance > 0:
            # 基础资产过多，应该卖出
            return OrderType.SELL if random.random() < 0.9 else OrderType.BUY
        else:
            return OrderType.BUY if random.random() < 0.5 else OrderType.SELL

    def _place_order(
        self,
        user: User,
        trading_pair: TradingPairType,
        order_type: OrderType,
        current_price: float,
        is_market: bool,
    ) -> None:
        """统一的订单放置方法。

        Args:
            user: 用户对象
            trading_pair: 交易对
            order_type: 订单类型
            current_price: 当前价格
            is_market: 是否使用市价单
        """
        engine = self.exchange.get_trading_pair(trading_pair)
        base_asset = trading_pair.base_asset

        if is_market:
            # 市价订单不传递价格
            self._place_market_order_internal(user, engine, order_type, base_asset)
        else:
            # 限价订单传递价格
            self._place_limit_order_internal(user, engine, order_type, base_asset, current_price)

    def _place_market_order_internal(
        self,
        user: User,
        engine: TradingPairEngine,
        order_type: OrderType,
        base_asset: AssetType,
    ) -> None:
        """内部市价订单放置方法。

        Args:
            user: 用户对象
            engine: 交易对引擎
            order_type: 订单类型
            base_asset: 基础资产类型
        """
        asset_type = AssetType.USDT if order_type == OrderType.MARKET_BUY else base_asset
        max_amount = user.get_available_balance(asset_type)

        if max_amount <= 0.01:  # 最小余额要求
            return

        amount = self._calculate_order_amount(max_amount, order_type)
        if amount <= 0:
            return

        # 最终余额检查
        if amount > user.get_available_balance(asset_type):
            return

        self._execute_market_order(engine, user, order_type, amount, base_asset)

    def _place_limit_order_internal(
        self,
        user: User,
        engine: TradingPairEngine,
        order_type: OrderType,
        base_asset: AssetType,
        current_price: float,
    ) -> None:
        """内部限价订单放置方法。

        Args:
            user: 用户对象
            engine: 交易对引擎
            order_type: 订单类型
            base_asset: 基础资产类型
            current_price: 当前价格
        """
        # 引入双向非对称偏移，增加价格波动性
        if order_type == OrderType.BUY:
            # 买单偏向向上报价，支撑价格
            target_price = current_price * (1 + random.uniform(-0.001, 0.008))
        else:  # SELL
            # 卖单偏向向下报价，但幅度较小
            target_price = current_price * (1 + random.uniform(-0.008, 0.001))

        if order_type == OrderType.BUY:
            max_usdt = user.get_available_balance(AssetType.USDT)
            if max_usdt <= 0.01:  # 最小余额要求
                return
            max_quantity = max_usdt / target_price
            # 确保不会超出可用余额
            required_usdt = max_quantity * target_price
            if required_usdt > max_usdt:
                max_quantity = max_usdt / target_price * 0.95  # 留5%缓冲
        else:  # SELL
            max_quantity = user.get_available_balance(base_asset)
            if max_quantity <= 0.0001:  # 最小余额要求
                return

        quantity = self._calculate_order_amount(max_quantity, order_type)
        if quantity <= 0:
            return

        # 最终余额检查
        if order_type == OrderType.BUY:
            required_usdt = quantity * target_price
            if required_usdt > user.get_available_balance(AssetType.USDT):
                return
        else:  # SELL
            if quantity > user.get_available_balance(base_asset):
                return

        self._execute_limit_order(engine, user, order_type, quantity, target_price, base_asset)

    def _calculate_order_amount(self, max_amount: float, order_type: OrderType) -> float:
        """计算订单数量。

        确保订单数量不超过可用余额，并设置合理的上下限。

        Args:
            max_amount: 最大可用数量
            order_type: 订单类型

        Returns:
            float: 计算的订单数量，不超过最大可用数量的80%
        """
        if max_amount <= 0:
            return 0.0

        # 使用80%的可用余额，避免全部用完
        max_safe_amount = max_amount * 0.8

        if order_type in [OrderType.MARKET_BUY, OrderType.BUY]:
            if order_type == OrderType.MARKET_BUY:
                # 市价买单：最小10 USDT，最大安全金额
                min_amount = min(10.0, max_safe_amount * 0.1)
                return max(min_amount, random.uniform(min_amount, max_safe_amount))
            else:
                # 限价买单：最小0.001，最大安全金额
                min_amount = min(0.001, max_safe_amount * 0.1)
                return max(min_amount, random.uniform(min_amount, max_safe_amount))
        else:
            # 卖单：最小0.001，最大安全金额
            min_amount = min(0.001, max_safe_amount * 0.1)
            return max(min_amount, random.uniform(min_amount, max_safe_amount))

    def _execute_market_order(
        self,
        engine: TradingPairEngine,
        user: User,
        order_type: OrderType,
        amount: float,
        base_asset: AssetType,
    ) -> None:
        """执行市价订单。

        Args:
            engine: 交易对引擎
            user: 用户对象
            order_type: 订单类型
            amount: 订单金额
            base_asset: 基础资产类型
        """
        if order_type == OrderType.MARKET_BUY:
            engine.place_order(user=user, order_type=OrderType.MARKET_BUY, quote_amount=amount)
            print_str = f'轮次{self.round_counter}: {user.username} 市价{order_type.value} {amount:.2f} USDT {engine.symbol}'
        else:
            engine.place_order(user=user, order_type=OrderType.MARKET_SELL, base_amount=amount)
            print_str = f'轮次{self.round_counter}: {user.username} 市价{order_type.value} {amount:.6f} {base_asset.value} {engine.symbol}'
        print(print_str)

    def _execute_limit_order(
        self,
        engine: TradingPairEngine,
        user: User,
        order_type: OrderType,
        quantity: float,
        price: float,
        base_asset: AssetType,
    ) -> None:
        """执行限价订单。

        Args:
            engine: 交易对引擎
            user: 用户对象
            order_type: 订单类型
            quantity: 订单数量
            price: 订单价格
            base_asset: 基础资产类型
        """
        engine.place_order(user=user, order_type=order_type, base_amount=quantity, price=price)
        print(
            f'轮次{self.round_counter}: {user.username} 限价{order_type.value} {quantity:.6f} {base_asset.value}@{price:.2f} {engine.symbol}'
        )

    def _cancel_random_order_in_pair(self, user: User, trading_pair: TradingPairType) -> None:
        """在指定交易对撤销订单。

        随机撤销用户在该交易对的任意一个活跃订单，避免USDT长期锁定。
        直接从用户的活跃订单列表中获取订单进行撤销。

        Args:
            user: 用户对象，包含用户的订单信息。
            trading_pair: 交易对，指定要撤销订单的交易市场。
        """
        engine = self.exchange.get_trading_pair(trading_pair)

        # 直接从用户的活跃订单中获取
        user_orders = self._get_user_orders_in_pair(user, trading_pair)

        if user_orders:
            # 随机选择一个订单撤销
            order = random.choice(user_orders)
        engine.cancel_order(order, user)
        order_type_name = '市价' if 'market' in order.order_type.value else '限价'
        print(
            f'轮次{self.round_counter}: {user.username} 在 {trading_pair.value} 撤销{order_type_name}订单成功'
        )

    def run_simulation(self) -> None:
        """运行完整的交易模拟。

        执行完整的交易模拟流程，包括用户创建、资金充值和多轮交易模拟。
        每轮交易都会输出当前轮次信息，便于跟踪模拟进度。

        流程：
            1. 创建测试用户
            2. 为用户充值初始资金
            3. 执行指定轮次的交易模拟
            4. 输出模拟完成信息

        Example:
            >>> simulator = TradingSimulator(user_count=3, trading_rounds=100)
            >>> simulator.run_simulation()
            === 开始模拟交易序列 ===
            用户数量: 3 个
            交易轮次: 100 轮
            交易对: [TradingPairType.BTC_USDT, TradingPairType.ETH_USDT]
            ...
            === 模拟完成，共100轮交易 ===
        """
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
        """创建交易模拟可视化图表。

        生成包含所有交易对价格走势的交互式HTML图表，支持多交易对切换查看。
        图表使用Plotly库生成，包含完整的交互功能和响应式设计。

        Args:
            output_file: 输出文件名，默认为'trading_simulation.html'。

        Returns:
            None: 将生成的图表保存到指定文件。

        Example:
            >>> simulator.create_visualization('my_trading_chart.html')
            价格图表已保存到: my_trading_chart.html
        """
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
        """打印模拟总结报告。

        输出详细的交易模拟结果，包括：
        1. 每个交易对的当前订单簿状态（前5个买卖单）
        2. 每个用户的资产情况（可用、锁定、总计）
        3. 每个用户的活跃订单详情

        报告格式清晰，便于分析模拟结果和用户行为。

        Example:
            === 模拟总结 ===

            === 交易对挂单情况 ===

            BTC/USDT:
              买单:
                价格: 50000.00, 数量: 0.500000
                ...
              卖单:
                价格: 51000.00, 数量: 0.800000
                ...
              当前价格: 50500.00

            === 用户资产情况 ===

            用户: Alice
              BTC: 可用 1.0000, 锁定 0.5000, 总计 1.5000
              USDT: 可用 5000.0000, 锁定 25000.0000, 总计 30000.0000
              活跃订单详情:
                BTC_USDT BUY: 2个订单
        """
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
        trading_rounds=5000,
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
