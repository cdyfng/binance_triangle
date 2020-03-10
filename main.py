# -*- coding:utf-8 -*-

"""
binance 模块使用演示

> 策略执行的几个步骤:
    Null
"""

import sys
import os

from quant import const
from quant.utils import tools
from quant.utils import logger
from quant.config import config
from quant.market import Market
from quant.trade import Trade
from quant.order import Order
from quant.market import Orderbook
from quant.position import Position
from quant.tasks import LoopRunTask
from quant.order import ORDER_ACTION_BUY, ORDER_ACTION_SELL, ORDER_STATUS_FILLED, ORDER_STATUS_PARTIAL_FILLED, ORDER_STATUS_SUBMITTED
from quant.order import TRADE_TYPE_OPEN_LONG, TRADE_TYPE_OPEN_SHORT, TRADE_TYPE_CLOSE_LONG, TRADE_TYPE_CLOSE_SHORT
#Swap order type
# TRADE_TYPE_OPEN_LONG = 1 
# TRADE_TYPE_OPEN_SHORT = 2 
# TRADE_TYPE_CLOSE_LONG = 3 
# TRADE_TYPE_CLOSE_SHORT = 4  


class MyStrategy:

    def __init__(self):
        """ 初始化
        """
        self.strategy = config.strategy
        self.platform = const.BINANCE
        self.account = config.accounts[0]["account"]
        self.access_key = config.accounts[0]["access_key"]
        self.secret_key = config.accounts[0]["secret_key"]
        self.symbol = config.symbol

        self.buy_open_order_no = None  # 开仓做多订单号
        self.buy_open_price = 0
        self.buy_open_quantity = "0.003"  # 开仓数量(USD)
        self.sell_close_order_no = None  # 多仓平仓订单号
        self.sell_close_time_down = 0  # 平仓倒计时
        self.bsud_usdt_price = 0
        self.btc_busd_relative = {}
        self.highest_price = 0
        self.lowest_price = 999999
        self.threshold = 0.0025
        self.six_price = [0, 0, 0, 0, 0, 0]
        self.six_amount = [0, 0, 0, 0, 0, 0]

        #self.current_price = None  # 当前盘口价格，为了方便，这里假设盘口价格为 卖一 和 买一 的平均值

        # 交易模块
        cc = {
            "strategy": self.strategy,
            "platform": self.platform,
            "symbol": self.symbol,
            "account": self.account,
            "access_key": self.access_key,
            "secret_key": self.secret_key,
            "order_update_callback": self.on_event_order_update,
            "position_update_callback": self.on_event_position_update
        }
        self.trader = Trade(**cc)

        # 订阅行情

        Market(const.MARKET_TYPE_ORDERBOOK, 'binance', 'BUSD/USDT', self.on_event_orderbook_update)
        Market(const.MARKET_TYPE_ORDERBOOK, 'binance', 'BTC/USDT', self.on_event_orderbook_update)
        Market(const.MARKET_TYPE_ORDERBOOK, 'binance', 'BTC/BUSD', self.on_event_orderbook_update)

        # 注册系统循环回调
        LoopRunTask.register(self.on_ticker, 1)  # 每隔1秒执行一次回调


    async def on_event_orderbook_update(self, orderbook: Orderbook):
        """ 订单薄更新
        """
        #logger.debug("orderbook:", orderbook, caller=self)
        ask1_price = float(orderbook.asks[0][0])  # 卖一价格
        bid1_price = float(orderbook.bids[0][0])  # 买一价格
        logger.debug("six prices :", self.six_price, caller=self)
        if orderbook.symbol == 'BUSD/USDT':
            self.six_price[0] = ask1_price
            self.six_price[1] = bid1_price
            self.six_amount[0] = float(orderbook.asks[0][1])
            self.six_amount[1] = float(orderbook.bids[0][1])
        elif orderbook.symbol == 'BTC/USDT':
            self.six_price[2] = ask1_price
            self.six_price[3] = bid1_price
            self.six_amount[2] = float(orderbook.asks[0][1])
            self.six_amount[3] = float(orderbook.bids[0][1])            
        elif orderbook.symbol == 'BTC/BUSD':
            self.six_price[4] = ask1_price
            self.six_price[5] = bid1_price
            self.six_amount[4] = float(orderbook.asks[0][1])
            self.six_amount[5] = float(orderbook.bids[0][1])            
        else:
            logger.error("error symbol ", orderbook.symbol)
            exit(0)

        if 0 in self.six_price:
            logger.info('prepare for 3 orderbooks ready... ', self.six_price)
            return 
    
        #p0, p1为take模式下的利润(未计算手续费)
        #p2, p3为make模式下的利润(未计算手续费)
        p0 = tools.round2(self.six_price[3]/self.six_price[0]/self.six_price[4], 6)
        p1 = tools.round2(self.six_price[1]*self.six_price[4]/self.six_price[2], 6)
        p2 = tools.round2(self.six_price[2]/self.six_price[1]/self.six_price[5], 6)
        p3 = tools.round2(self.six_price[0]*self.six_price[4]/self.six_price[3], 6)
        #logger.info(self.six_price[0], self.six_price[4], self.six_price[3])
        logger.info('basic profit:', p0, p1, p2, p3)
        action = []
        if p0 > self.threshold:
            action = [['BUSD/USDT', 'Buy', 0], ['BTC/BUSD', 'Buy', 0], ['BTC/USDT', 'Sell', 0]]
        elif p1 > self.threshold:
            action = [['BUSD/USDT', 'Sell', 0], ['BTC/USDT', 'Buy', 0], ['BTC/BUSD', 'Sell', 0]]

        if p0 >1.002 or p1 > 1.002:
            logger.info('basic profit > 1.002', self.six_price, p0,  p1, p2, p3)
            s = "triangle ok "
            os.system('say '+ s)
            logger.info('say ok  > 1.002', self.six_price, p0,  p1, p2, p3)        

        #选择一个价格变化最大的交易对，先开始尝试交易，成功

    async def on_event_order_update(self, order: Order):
        """ 订单状态更新
        """
        logger.info("order update:", order, caller=self)
        s = "update "
        os.system('say '+ s)
 
    async def on_event_position_update(self, position: Position):
        """ 持仓更新
        """
        logger.info("position:", position, caller=self)

    async def on_ticker(self, *args, **kwargs):
        """ 系统循环回调，每秒钟执行一次
        """
        logger.info("do ticker ...", caller=self)
        # if self.sell_close_time_down > 0:
        #     self.sell_close_time_down -= 1
        #     if self.sell_close_time_down <= 0:
        #         price = self.current_price # 当前盘口价格，
        #         new_price = tools.float_to_str(price)  # 将价格转换为字符串，保持精度
        #         order_no, error = await self.trader.create_order(TRADE_TYPE_OPEN_SHORT, new_price, self.buy_open_quantity)
        #         if error:
        #             logger.error("create order error! error:", error, caller=self)
        #             return
        #         logger.info("create sell close order:", order_no, caller=self)

    def reset_process(self, quantity = tools.float_to_str(0.003)):
        logger.info("reset_process ", caller=self)   
        self.buy_open_order_no = None  # 开仓做多订单号
        self.buy_open_price = 0
        self.buy_open_quantity = tools.float_to_str(quantity)  # 开仓数量(USD)
        self.sell_close_order_no = None  # 多仓平仓订单号
        self.sell_close_time_down = 0  # 平仓倒计时
        self.highest_price = 0
        self.lowest_price = 999999
        self.threshold = 0.001        

    async def recreate_order(self, quantity = tools.float_to_str(0.003)):
        pass


def main():
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = None

    from quant.quant import quant
    quant.initialize(config_file)
    MyStrategy()
    quant.start()


if __name__ == '__main__':
    main()
