"""交易所使用示例"""

from .exchange import Exchange
from .models import AssetType, OrderType


def run_exchange_demo():
    """运行交易所演示"""
    print('=== TradeMasterOnline 交易所演示 ===\n')
    
    # 创建交易所实例
    exchange = Exchange()
    
    # 显示初始状态
    print('1. 初始状态:')
    btc_pair = exchange.get_trading_pair(AssetType.BTC)
    print(f'   BTC/USDT 当前价格: ${btc_pair.current_price:,.2f}')
    print()
    
    # 用户1下买单
    print('2. 用户1下买单:')
    buy_order1 = exchange.place_order(
        user_id='user1',
        order_type=OrderType.BUY,
        asset=AssetType.BTC,
        quantity=1.0,
        price=50000.0
    )
    print(f'   买单ID: {buy_order1.id}')
    print(f'   数量: {buy_order1.quantity} BTC')
    print(f'   价格: ${buy_order1.price:,.2f}')
    print()
    
    # 用户2下卖单
    print('3. 用户2下卖单:')
    sell_order1 = exchange.place_order(
        user_id='user2',
        order_type=OrderType.SELL,
        asset=AssetType.BTC,
        quantity=0.5,
        price=50000.0
    )
    print(f'   卖单ID: {sell_order1.id}')
    print(f'   数量: {sell_order1.quantity} BTC')
    print(f'   价格: ${sell_order1.price:,.2f}')
    print()
    
    # 显示成交情况
    print('4. 成交情况:')
    trades = exchange.get_recent_trades(AssetType.BTC)
    for trade in trades:
        print(f'   成交ID: {trade.id}')
        print(f'   数量: {trade.quantity} BTC')
        print(f'   价格: ${trade.price:,.2f}')
        print(f'   时间: {trade.timestamp}')
        print()
    
    # 显示订单状态
    print('5. 订单状态:')
    buy_order = exchange.get_order(buy_order1.id)
    sell_order = exchange.get_order(sell_order1.id)
    
    print(f'   买单状态: {buy_order.status}')
    print(f'   已成交: {buy_order.filled_quantity} BTC')
    print(f'   剩余: {buy_order.remaining_quantity} BTC')
    print()
    
    print(f'   卖单状态: {sell_order.status}')
    print(f'   已成交: {sell_order.filled_quantity} BTC')
    print(f'   剩余: {sell_order.remaining_quantity} BTC')
    print()
    
    # 显示更新后的价格
    print('6. 更新后的价格:')
    btc_pair = exchange.get_trading_pair(AssetType.BTC)
    print(f'   BTC/USDT 当前价格: ${btc_pair.current_price:,.2f}')
    print()
    
    # 显示订单簿
    print('7. 订单簿:')
    order_book = exchange.get_order_book(AssetType.BTC)
    
    print('   买单:')
    for order in order_book[OrderType.BUY][:3]:  # 显示前3个买单
        print(f'     ${order.price:,.2f} - {order.remaining_quantity} BTC')
    
    print('   卖单:')
    for order in order_book[OrderType.SELL][:3]:  # 显示前3个卖单
        print(f'     ${order.price:,.2f} - {order.remaining_quantity} BTC')
    print()
    
    # 用户3下更高价格的买单
    print('8. 用户3下更高价格的买单:')
    buy_order2 = exchange.place_order(
        user_id='user3',
        order_type=OrderType.BUY,
        asset=AssetType.BTC,
        quantity=0.3,
        price=50100.0
    )
    print(f'   买单ID: {buy_order2.id}')
    print(f'   数量: {buy_order2.quantity} BTC')
    print(f'   价格: ${buy_order2.price:,.2f}')
    print()
    
    # 用户4下更低价格的卖单
    print('9. 用户4下更低价格的卖单:')
    sell_order2 = exchange.place_order(
        user_id='user4',
        order_type=OrderType.SELL,
        asset=AssetType.BTC,
        quantity=0.2,
        price=50050.0
    )
    print(f'   卖单ID: {sell_order2.id}')
    print(f'   数量: {sell_order2.quantity} BTC')
    print(f'   价格: ${sell_order2.price:,.2f}')
    print()
    
    # 显示最终成交情况
    print('10. 最终成交情况:')
    trades = exchange.get_recent_trades(AssetType.BTC)
    for trade in trades:
        print(f'   成交ID: {trade.id}')
        print(f'   数量: {trade.quantity} BTC')
        print(f'   价格: ${trade.price:,.2f}')
        print(f'   时间: {trade.timestamp}')
        print()
    
    # 显示最终价格
    print('11. 最终价格:')
    btc_pair = exchange.get_trading_pair(AssetType.BTC)
    print(f'   BTC/USDT 当前价格: ${btc_pair.current_price:,.2f}')
    print()
    
    print('=== 演示完成 ===')


if __name__ == '__main__':
    run_exchange_demo() 