"""交易所使用示例 - 带可视化功能"""

from loguru import logger

from tmo import AssetType, Exchange, ExchangeVisualizer, OrderType


# 配置 loguru 只显示 INFO 及以上级别的日志
logger.remove()
logger.add(lambda msg: print(msg, end=''), level='INFO')


def run_exchange_demo():
    """运行交易所演示"""
    logger.info('=== TradeMasterOnline 交易所演示 ===')

    # 创建交易所实例和可视化器
    exchange = Exchange()
    visualizer = ExchangeVisualizer()

    # 记录初始状态
    visualizer.record_snapshot(exchange, '初始状态', '交易所初始化完成')

    # 显示初始状态
    logger.info('1. 初始状态:')
    btc_pair = exchange.get_trading_pair(AssetType.BTC)
    logger.info(f'   BTC/USDT 当前价格: ${btc_pair.current_price:,.2f}')

    # 用户1下买单
    logger.info('2. 用户1下买单:')
    buy_order1 = exchange.place_order(
        user_id='user1', order_type=OrderType.BUY, asset=AssetType.BTC, quantity=1.0, price=50000.0
    )
    visualizer.record_snapshot(
        exchange,
        '用户1下买单',
        f'用户1下买单: {buy_order1.quantity} BTC @ ${buy_order1.price:,.2f}',
    )
    logger.info(f'   买单ID: {buy_order1.id}')
    logger.info(f'   数量: {buy_order1.quantity} BTC')
    logger.info(f'   价格: ${buy_order1.price:,.2f}')

    # 用户2下卖单（部分成交）
    logger.info('3. 用户2下卖单:')
    sell_order1 = exchange.place_order(
        user_id='user2', order_type=OrderType.SELL, asset=AssetType.BTC, quantity=0.5, price=50000.0
    )
    visualizer.record_snapshot(
        exchange,
        '用户2下卖单',
        f'用户2下卖单: {sell_order1.quantity} BTC @ ${sell_order1.price:,.2f}',
    )
    logger.info(f'   卖单ID: {sell_order1.id}')
    logger.info(f'   数量: {sell_order1.quantity} BTC')
    logger.info(f'   价格: ${sell_order1.price:,.2f}')

    # 记录成交后状态
    recent_trades = exchange.get_recent_trades(AssetType.BTC)
    if recent_trades:
        latest_trade = recent_trades[-1]
        visualizer.record_snapshot(
            exchange,
            '成交后状态',
            f'成交: {latest_trade.quantity} BTC @ ${latest_trade.price:,.2f}',
        )
        logger.info('4. 成交情况:')
        logger.info(f'   成交ID: {latest_trade.id}')
        logger.info(f'   数量: {latest_trade.quantity} BTC')
        logger.info(f'   价格: ${latest_trade.price:,.2f}')
        logger.info(f'   时间: {latest_trade.timestamp}')

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
    btc_pair = exchange.get_trading_pair(AssetType.BTC)
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
    visualizer.record_snapshot(
        exchange,
        '用户3下买单',
        f'用户3下买单: {buy_order2.quantity} BTC @ ${buy_order2.price:,.2f}',
    )
    logger.info(f'   买单ID: {buy_order2.id}')
    logger.info(f'   数量: {buy_order2.quantity} BTC')
    logger.info(f'   价格: ${buy_order2.price:,.2f}')

    # 用户4下卖单（与用户3的买单成交）
    logger.info('9. 用户4下卖单:')
    sell_order2 = exchange.place_order(
        user_id='user4', order_type=OrderType.SELL, asset=AssetType.BTC, quantity=0.3, price=50100.0
    )
    visualizer.record_snapshot(
        exchange,
        '用户4下卖单',
        f'用户4下卖单: {sell_order2.quantity} BTC @ ${sell_order2.price:,.2f}',
    )
    logger.info(f'   卖单ID: {sell_order2.id}')
    logger.info(f'   数量: {sell_order2.quantity} BTC')
    logger.info(f'   价格: ${sell_order2.price:,.2f}')

    # 记录新的成交后状态
    recent_trades = exchange.get_recent_trades(AssetType.BTC)
    if len(recent_trades) > 1:
        latest_trade = recent_trades[-1]
        visualizer.record_snapshot(
            exchange,
            '第二次成交',
            f'成交: {latest_trade.quantity} BTC @ ${latest_trade.price:,.2f}',
        )
        logger.info('10. 新的成交:')
        logger.info(f'    成交ID: {latest_trade.id}')
        logger.info(f'    数量: {latest_trade.quantity} BTC')
        logger.info(f'    价格: ${latest_trade.price:,.2f}')

    # 用户5取消订单
    logger.info('11. 用户5下买单然后取消:')
    buy_order3 = exchange.place_order(
        user_id='user5', order_type=OrderType.BUY, asset=AssetType.BTC, quantity=0.2, price=50200.0
    )
    visualizer.record_snapshot(
        exchange,
        '用户5下买单',
        f'用户5下买单: {buy_order3.quantity} BTC @ ${buy_order3.price:,.2f}',
    )
    logger.info(f'   买单ID: {buy_order3.id}')

    # 取消订单
    exchange.cancel_order(buy_order3.id)
    buy_order3 = exchange.get_order(buy_order3.id)
    visualizer.record_snapshot(
        exchange,
        '用户5取消订单',
        f'用户5取消订单: {buy_order3.quantity} BTC @ ${buy_order3.price:,.2f}',
    )
    logger.info(f'   订单已取消，状态: {buy_order3.status}')

    logger.info('=== 演示完成 ===')

    # 生成可视化图表
    logger.info('正在生成可视化图表...')
    visualizer.create_visualization(exchange, 'examples/exchange_demo.html')

    logger.info('可视化图表已生成完成！')
    logger.info("请在浏览器中打开 'examples/exchange_demo.html' 查看交互式图表")


if __name__ == '__main__':
    run_exchange_demo()
