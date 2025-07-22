"""模拟交易所核心逻辑"""

import uuid
from datetime import datetime

from loguru import logger

from .typing import Asset, AssetType, Order, OrderType, Trade, TradingPair


class Exchange:
    """模拟交易所 - 提供完整的交易撮合系统"""

    def __init__(self):
        """初始化交易所"""
        # 支持的资产
        self.assets: dict[AssetType, Asset] = {
            AssetType.USDT: Asset(
                symbol=AssetType.USDT, name='Tether USD', description='美元稳定币'
            ),
            AssetType.BTC: Asset(symbol=AssetType.BTC, name='Bitcoin', description='比特币'),
        }

        # 交易对
        self.trading_pairs: dict[str, TradingPair] = {
            'BTC/USDT': TradingPair(
                base_asset=AssetType.BTC, quote_asset=AssetType.USDT, current_price=50000.0
            )  # 初始价格
        }

        # 订单簿：按价格排序的订单列表
        self.order_books: dict[str, dict[OrderType, list[Order]]] = {
            'BTC/USDT': {
                OrderType.BUY: [],  # 买单按价格降序排列
                OrderType.SELL: [],  # 卖单按价格升序排列
            }
        }

        # 成交记录
        self.trades: list[Trade] = []

        # 订单索引
        self.orders: dict[str, Order] = {}

    # ====================
    # 操作接口 - 订单管理
    # ====================

    def place_order(
        self, user_id: str, order_type: OrderType, asset: AssetType, quantity: float, price: float
    ) -> Order:
        """下单并立即执行匹配"""
        order = Order(
            id=str(uuid.uuid4()),
            user_id=user_id,
            order_type=order_type,
            asset=asset,
            quantity=quantity,
            price=price,
        )

        logger.debug(
            f'用户 {user_id} 下 {order_type.value} 单: {quantity} {asset.value} @ ${price:,.2f}'
        )

        # 存储订单
        self.orders[order.id] = order

        # 添加到订单簿并立即匹配
        self._process_new_order(order)

        return order

    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        order = self.orders.get(order_id)
        if not order or order.is_filled:
            logger.debug(f'无法取消订单 {order_id}: 订单不存在或已成交')
            return False

        # 从订单簿中移除
        self._remove_from_order_book(order)

        # 更新订单状态
        order.status = 'cancelled'
        logger.debug(
            f'用户 {order.user_id} 取消订单: {order.quantity} {order.asset.value} @ ${order.price:,.2f}'
        )

        return True

    # ====================
    # 状态快照接口
    # ====================

    def get_state_snapshot(self) -> dict:
        """获取交易所完整状态快照"""
        return {
            'assets': self.assets.copy(),
            'trading_pairs': {
                symbol: {
                    'base_asset': pair.base_asset,
                    'quote_asset': pair.quote_asset,
                    'current_price': pair.current_price,
                    'last_update': pair.last_update,
                }
                for symbol, pair in self.trading_pairs.items()
            },
            'order_books': {
                symbol: {
                    'BUY': [order.model_dump() for order in orders[OrderType.BUY]],
                    'SELL': [order.model_dump() for order in orders[OrderType.SELL]],
                }
                for symbol, orders in self.order_books.items()
            },
            'trades': [trade.model_dump() for trade in self.trades],
            'orders': {order_id: order.model_dump() for order_id, order in self.orders.items()},
        }

    # ====================
    # 查询接口
    # ====================

    def get_market_price(self, asset: AssetType) -> float:
        """获取交易对当前市场价格"""
        pair_symbol = f'{asset.value}/USDT'
        if pair_symbol in self.trading_pairs:
            return self.trading_pairs[pair_symbol].current_price
        raise ValueError(f'不存在的交易对: {pair_symbol}')

    def get_market_depth(self, asset: AssetType) -> dict:
        """获取交易对市场深度信息"""
        pair_symbol = f'{asset.value}/USDT'
        if pair_symbol not in self.order_books:
            return {'bids': [], 'asks': []}

        order_book = self.order_books[pair_symbol]
        return {
            'bids': [
                {'price': order.price, 'quantity': order.remaining_quantity}
                for order in order_book[OrderType.BUY]
            ],
            'asks': [
                {'price': order.price, 'quantity': order.remaining_quantity}
                for order in order_book[OrderType.SELL]
            ],
        }

    def get_market_summary(self, asset: AssetType) -> dict:
        """获取交易对市场摘要"""
        pair_symbol = f'{asset.value}/USDT'
        if pair_symbol not in self.trading_pairs:
            raise ValueError(f'不存在的交易对: {pair_symbol}')

        trading_pair = self.trading_pairs[pair_symbol]
        recent_trades = self._get_recent_trades_for_asset(asset, limit=50)
        order_book = self.order_books[pair_symbol]

        return {
            'symbol': pair_symbol,
            'current_price': trading_pair.current_price,
            'last_update': trading_pair.last_update,
            'total_bids': len(order_book[OrderType.BUY]),
            'total_asks': len(order_book[OrderType.SELL]),
            'recent_trades': len(recent_trades),
            'best_bid': order_book[OrderType.BUY][0].price if order_book[OrderType.BUY] else None,
            'best_ask': order_book[OrderType.SELL][0].price if order_book[OrderType.SELL] else None,
        }

    def get_order_book(self, asset: AssetType) -> dict[OrderType, list[Order]]:
        """获取订单簿"""
        pair_symbol = f'{asset.value}/USDT'
        if pair_symbol in self.order_books:
            return self.order_books[pair_symbol].copy()
        return {OrderType.BUY: [], OrderType.SELL: []}

    def get_trading_pair(self, asset: AssetType) -> TradingPair | None:
        """获取交易对信息"""
        pair_symbol = f'{asset.value}/USDT'
        return self.trading_pairs.get(pair_symbol)

    def get_recent_trades(self, asset: AssetType, limit: int = 10) -> list[Trade]:
        """获取最近的成交记录"""
        return self._get_recent_trades_for_asset(asset, limit)

    def get_order(self, order_id: str) -> Order | None:
        """获取订单信息"""
        return self.orders.get(order_id)

    def get_order_status(self, order_id: str) -> dict:
        """获取订单详细状态"""
        order = self.orders.get(order_id)
        if not order:
            raise ValueError(f'不存在的订单: {order_id}')

        return {
            'order': order.model_dump(),
            'trading_pair': f'{order.asset.value}/USDT',
            'filled_percentage': (order.filled_quantity / order.quantity * 100)
            if order.quantity > 0
            else 0,
            'is_active': order.status in ['pending', 'partially_filled'],
        }

    # ====================
    # 内部实现 - 私有方法
    # ====================

    def _process_new_order(self, order: Order) -> None:
        """处理新订单：添加到订单簿并执行匹配"""
        pair_symbol = f'{order.asset.value}/USDT'
        if pair_symbol not in self.order_books:
            return

        # 添加到订单簿
        self._add_to_order_book(order)

        # 立即执行匹配
        self._match_orders(pair_symbol)

    def _add_to_order_book(self, order: Order) -> None:
        """将订单添加到订单簿"""
        pair_symbol = f'{order.asset.value}/USDT'
        order_list = self.order_books[pair_symbol][order.order_type]

        if order.order_type == OrderType.BUY:
            # 买单按价格降序排列（价格高的优先）
            self._insert_buy_order(order_list, order)
        else:
            # 卖单按价格升序排列（价格低的优先）
            self._insert_sell_order(order_list, order)

    def _insert_buy_order(self, order_list: list[Order], order: Order) -> None:
        """插入买单（价格降序）"""
        for i, existing_order in enumerate(order_list):
            if order.price > existing_order.price:
                order_list.insert(i, order)
                return
        order_list.append(order)

    def _insert_sell_order(self, order_list: list[Order], order: Order) -> None:
        """插入卖单（价格升序）"""
        for i, existing_order in enumerate(order_list):
            if order.price < existing_order.price:
                order_list.insert(i, order)
                return
        order_list.append(order)

    def _remove_from_order_book(self, order: Order) -> None:
        """从订单簿中移除订单"""
        pair_symbol = f'{order.asset.value}/USDT'
        if pair_symbol in self.order_books:
            order_list = self.order_books[pair_symbol][order.order_type]
            if order in order_list:
                order_list.remove(order)

    def _match_orders(self, pair_symbol: str) -> None:
        """匹配订单"""
        if pair_symbol not in self.order_books:
            return

        buy_orders = self.order_books[pair_symbol][OrderType.BUY]
        sell_orders = self.order_books[pair_symbol][OrderType.SELL]

        while buy_orders and sell_orders:
            buy_order = buy_orders[0]
            sell_order = sell_orders[0]

            # 检查是否可以成交
            if buy_order.price >= sell_order.price:
                # 可以成交
                trade = self._execute_trade(buy_order, sell_order)
                self.trades.append(trade)

                # 更新订单状态
                self._update_order_status(buy_order)
                self._update_order_status(sell_order)

                # 更新交易对价格
                self._update_trading_pair_price(pair_symbol, trade.price)

                # 清理已完成的订单
                self._cleanup_filled_orders(pair_symbol)
            else:
                # 无法成交，退出循环
                break

    def _execute_trade(self, buy_order: Order, sell_order: Order) -> Trade:
        """执行交易"""
        # 确定成交数量和价格
        trade_quantity = min(buy_order.remaining_quantity, sell_order.remaining_quantity)
        trade_price = sell_order.price  # 按卖单价格成交

        # 更新订单已成交数量
        buy_order.filled_quantity += trade_quantity
        sell_order.filled_quantity += trade_quantity

        # 创建成交记录
        trade = Trade(
            id=str(uuid.uuid4()),
            buy_order_id=buy_order.id,
            sell_order_id=sell_order.id,
            asset=buy_order.asset,
            quantity=trade_quantity,
            price=trade_price,
        )

        logger.debug(f'成交: {trade_quantity} {buy_order.asset.value} @ ${trade_price:,.2f}')
        return trade

    def _update_order_status(self, order: Order) -> None:
        """更新订单状态"""
        if order.is_filled:
            order.status = 'filled'
        elif order.is_partially_filled:
            order.status = 'partially_filled'

    def _update_trading_pair_price(self, pair_symbol: str, price: float) -> None:
        """更新交易对价格"""
        if pair_symbol in self.trading_pairs:
            old_price = self.trading_pairs[pair_symbol].current_price
            self.trading_pairs[pair_symbol].current_price = price
            self.trading_pairs[pair_symbol].last_update = datetime.now()

            if old_price != price:
                logger.debug(f'{pair_symbol} 价格更新: ${old_price:,.2f} -> ${price:,.2f}')

    def _cleanup_filled_orders(self, pair_symbol: str) -> None:
        """清理已完成的订单"""
        for order_type in [OrderType.BUY, OrderType.SELL]:
            order_list = self.order_books[pair_symbol][order_type]
            # 移除已完成的订单
            order_list[:] = [order for order in order_list if not order.is_filled]

    def _get_recent_trades_for_asset(self, asset: AssetType, limit: int) -> list[Trade]:
        """获取特定资产的最近成交记录"""
        asset_trades = [trade for trade in self.trades if trade.asset == asset]
        return sorted(asset_trades, key=lambda x: x.timestamp, reverse=True)[:limit]
