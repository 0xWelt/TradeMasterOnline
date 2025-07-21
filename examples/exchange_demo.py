"""交易所使用示例 - 带可视化功能"""

import random

from loguru import logger

from tmo import AssetType, Exchange, ExchangeVisualizer, OrderType


# 配置 loguru 只显示 INFO 及以上级别的日志
logger.remove()
logger.add(lambda msg: print(msg, end=''), level='INFO')


def generate_random_trading_sequence(
    exchange: Exchange,
    visualizer: ExchangeVisualizer,
    num_orders: int = 20,
    base_price: float = 50000.0,
):
    """生成随机交易序列"""
    logger.info(f'=== 开始生成 {num_orders} 个随机交易 ===')

    # 记录初始状态
    visualizer.record_snapshot(exchange, '初始状态', '交易所初始化完成')
    logger.info('1. 初始状态:')
    btc_pair = exchange.get_trading_pair(AssetType.BTC)
    logger.info(f'   BTC/USDT 当前价格: ${btc_pair.current_price:,.2f}')

    # 用户ID池
    user_ids = [f'user{i}' for i in range(1, 11)]

    # 价格波动范围
    price_volatility = 0.02  # 2% 的价格波动

    current_price = base_price

    for i in range(num_orders):
        # 随机选择用户
        user_id = random.choice(user_ids)

        # 随机决定订单类型（60% 买单，40% 卖单）
        order_type = OrderType.BUY if random.random() < 0.6 else OrderType.SELL

        # 生成随机价格（基于当前价格，有一定波动）
        price_change = random.uniform(-price_volatility, price_volatility)
        price = current_price * (1 + price_change)
        price = max(price, base_price * 0.95)  # 最低不低于基准价格的95%
        price = min(price, base_price * 1.05)  # 最高不超过基准价格的105%

        # 生成随机数量（0.1 到 2.0 BTC）
        quantity = random.uniform(0.1, 2.0)
        quantity = round(quantity, 2)  # 保留两位小数

        # 下订单
        order = exchange.place_order(
            user_id=user_id,
            order_type=order_type,
            asset=AssetType.BTC,
            quantity=quantity,
            price=price,
        )

        # 更新当前价格（基于最新成交价）
        btc_pair = exchange.get_trading_pair(AssetType.BTC)
        current_price = btc_pair.current_price

        # 记录快照
        step_name = f'步骤{i + 1}: {user_id}下{order_type.value}单'
        description = f'{user_id}下{order_type.value}单: {quantity} BTC @ ${price:,.2f}'
        visualizer.record_snapshot(exchange, step_name, description)

        # 显示订单信息
        logger.info(f'{i + 2}. {step_name}:')
        logger.info(f'   订单ID: {order.id}')
        logger.info(f'   数量: {quantity} BTC')
        logger.info(f'   价格: ${price:,.2f}')
        logger.info(f'   当前价格: ${current_price:,.2f}')

        # 检查是否有成交
        recent_trades = exchange.get_recent_trades(AssetType.BTC)
        if recent_trades and len(recent_trades) > 0:
            latest_trade = recent_trades[-1]
            # 检查是否是新成交（通过比较时间戳）
            if hasattr(latest_trade, '_is_new_trade') and not latest_trade._is_new_trade:
                logger.info(f'   成交: {latest_trade.quantity} BTC @ ${latest_trade.price:,.2f}')
                latest_trade._is_new_trade = True

        # 每5个订单显示一次订单簿摘要
        if (i + 1) % 5 == 0:
            logger.info(f'   --- 订单簿摘要 (步骤 {i + 1}) ---')
            order_book = exchange.get_order_book(AssetType.BTC)
            if order_book:
                buy_orders = order_book[OrderType.BUY][:3]
                sell_orders = order_book[OrderType.SELL][:3]

                if buy_orders:
                    logger.info(
                        f'   买单: ${buy_orders[0].price:,.2f} - {buy_orders[0].remaining_quantity} BTC'
                    )
                if sell_orders:
                    logger.info(
                        f'   卖单: ${sell_orders[0].price:,.2f} - {sell_orders[0].remaining_quantity} BTC'
                    )
            logger.info('   --- 摘要结束 ---')

    logger.info('=== 随机交易序列生成完成 ===')


def run_exchange_demo():
    """运行交易所演示"""
    logger.info('=== TradeMasterOnline 交易所演示 - 随机交易序列 ===')

    # 设置随机种子以确保可重现性
    random.seed(42)

    # 创建交易所实例和可视化器
    exchange = Exchange()
    visualizer = ExchangeVisualizer()

    # 生成随机交易序列
    generate_random_trading_sequence(exchange, visualizer, num_orders=25)

    # 显示最终统计信息
    logger.info('=== 最终统计信息 ===')

    # 价格统计
    btc_pair = exchange.get_trading_pair(AssetType.BTC)
    logger.info(f'最终价格: ${btc_pair.current_price:,.2f}')

    # 订单统计
    total_orders = len(exchange.orders)
    logger.info(f'总订单数: {total_orders}')

    # 成交统计
    total_trades = len(exchange.trades)
    logger.info(f'总成交数: {total_trades}')

    # 用户活跃度统计
    user_activity = {}
    for order in exchange.orders.values():
        user_id = order.user_id
        user_activity[user_id] = user_activity.get(user_id, 0) + 1

    logger.info('用户活跃度:')
    for user_id, count in sorted(user_activity.items(), key=lambda x: x[1], reverse=True):
        logger.info(f'  {user_id}: {count} 个订单')

    # 订单状态统计
    status_counts = {}
    for order in exchange.orders.values():
        status = order.status
        status_counts[status] = status_counts.get(status, 0) + 1

    logger.info('订单状态统计:')
    for status, count in status_counts.items():
        logger.info(f'  {status}: {count} 个订单')

    # 显示最终订单簿
    logger.info('最终订单簿:')
    order_book = exchange.get_order_book(AssetType.BTC)
    if order_book:
        buy_orders = order_book[OrderType.BUY][:5]
        sell_orders = order_book[OrderType.SELL][:5]

        logger.info('  买单:')
        for order in buy_orders:
            logger.info(
                f'    ${order.price:,.2f} - {order.remaining_quantity} BTC ({order.user_id})'
            )

        logger.info('  卖单:')
        for order in sell_orders:
            logger.info(
                f'    ${order.price:,.2f} - {order.remaining_quantity} BTC ({order.user_id})'
            )

    logger.info('=== 演示完成 ===')

    # 生成可视化图表
    logger.info('正在生成可视化图表...')
    visualizer.create_visualization(exchange, 'examples/exchange_demo.html')

    logger.info('可视化图表已生成完成！')
    logger.info("请在浏览器中打开 'examples/exchange_demo.html' 查看交互式图表")


if __name__ == '__main__':
    run_exchange_demo()
