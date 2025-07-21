"""交易所使用示例"""

from loguru import logger

from tmo.exchange import Exchange
from tmo.models import AssetType, OrderType


def run_exchange_demo():
    """运行交易所演示"""
    logger.info('=== TradeMasterOnline 交易所演示 ===')

    # 创建交易所实例
    exchange = Exchange()

    # 显示初始状态
    logger.info('1. 初始状态:')
    btc_pair = exchange.get_trading_pair(AssetType.BTC)
    logger.info(f'   BTC/USDT 当前价格: ${btc_pair.current_price:,.2f}')

    # 用户1下买单
    logger.info('2. 用户1下买单:')
    buy_order1 = exchange.place_order(
        user_id='user1', order_type=OrderType.BUY, asset=AssetType.BTC, quantity=1.0, price=50000.0
    )
    logger.info(f'   买单ID: {buy_order1.id}')
    logger.info(f'   数量: {buy_order1.quantity} BTC')
    logger.info(f'   价格: ${buy_order1.price:,.2f}')

    # 用户2下卖单
    logger.info('3. 用户2下卖单:')
    sell_order1 = exchange.place_order(
        user_id='user2', order_type=OrderType.SELL, asset=AssetType.BTC, quantity=0.5, price=50000.0
    )
    logger.info(f'   卖单ID: {sell_order1.id}')
    logger.info(f'   数量: {sell_order1.quantity} BTC')
    logger.info(f'   价格: ${sell_order1.price:,.2f}')

    # 显示成交情况
    logger.info('4. 成交情况:')
    trades = exchange.get_recent_trades(AssetType.BTC)
    for trade in trades:
        logger.info(f'   成交ID: {trade.id}')
        logger.info(f'   数量: {trade.quantity} BTC')
        logger.info(f'   价格: ${trade.price:,.2f}')
        logger.info(f'   时间: {trade.timestamp}')

    # 显示订单状态
    logger.info('5. 订单状态:')
    buy_order = exchange.get_order(buy_order1.id)
    sell_order = exchange.get_order(sell_order1.id)

    logger.info(f'   买单状态: {buy_order.status}')
    logger.info(f'   已成交: {buy_order.filled_quantity} BTC')
    logger.info(f'   剩余: {buy_order.remaining_quantity} BTC')

    logger.info(f'   卖单状态: {sell_order.status}')
    logger.info(f'   已成交: {sell_order.filled_quantity} BTC')
    logger.info(f'   剩余: {sell_order.remaining_quantity} BTC')

    # 显示更新后的价格
    logger.info('6. 更新后的价格:')
    btc_pair = exchange.get_trading_pair(AssetType.BTC)
    logger.info(f'   BTC/USDT 当前价格: ${btc_pair.current_price:,.2f}')

    # 显示订单簿
    logger.info('7. 订单簿:')
    order_book = exchange.get_order_book(AssetType.BTC)

    logger.info('   买单:')
    for order in order_book[OrderType.BUY][:3]:  # 显示前3个买单
        logger.info(f'     ${order.price:,.2f} - {order.remaining_quantity} BTC')

    logger.info('   卖单:')
    for order in order_book[OrderType.SELL][:3]:  # 显示前3个卖单
        logger.info(f'     ${order.price:,.2f} - {order.remaining_quantity} BTC')

    # 用户3下更高价格的买单
    logger.info('8. 用户3下更高价格的买单:')
    buy_order2 = exchange.place_order(
        user_id='user3', order_type=OrderType.BUY, asset=AssetType.BTC, quantity=0.3, price=50100.0
    )
    logger.info(f'   买单ID: {buy_order2.id}')
    logger.info(f'   数量: {buy_order2.quantity} BTC')
    logger.info(f'   价格: ${buy_order2.price:,.2f}')

    # 用户4下更低价格的卖单
    logger.info('9. 用户4下更低价格的卖单:')
    sell_order2 = exchange.place_order(
        user_id='user4', order_type=OrderType.SELL, asset=AssetType.BTC, quantity=0.2, price=50050.0
    )
    logger.info(f'   卖单ID: {sell_order2.id}')
    logger.info(f'   数量: {sell_order2.quantity} BTC')
    logger.info(f'   价格: ${sell_order2.price:,.2f}')

    # 显示最终成交情况
    logger.info('10. 最终成交情况:')
    trades = exchange.get_recent_trades(AssetType.BTC)
    for trade in trades:
        logger.info(f'   成交ID: {trade.id}')
        logger.info(f'   数量: {trade.quantity} BTC')
        logger.info(f'   价格: ${trade.price:,.2f}')
        logger.info(f'   时间: {trade.timestamp}')

    # 显示最终价格
    logger.info('11. 最终价格:')
    btc_pair = exchange.get_trading_pair(AssetType.BTC)
    logger.info(f'   BTC/USDT 当前价格: ${btc_pair.current_price:,.2f}')

    logger.info('=== 演示完成 ===')


if __name__ == '__main__':
    run_exchange_demo()
