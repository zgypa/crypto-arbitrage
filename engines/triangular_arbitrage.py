import time
from time import strftime
import grequests
from exchanges.loader import EngineLoader
import logging

LOG_LEVEL=logging.DEBUG

class CryptoEngineTriArbitrage(object):
    
    def __init__(self, exchange, mock=False):
        self.exchange = exchange
        self.mock = mock
        self.minProfitUSDT = 0.3
        self.hasOpenOrder = True # always assume there are open orders first
        self.openOrderCheckCount = 0
      
        self.engine = EngineLoader.getEngine(self.exchange['exchange'], self.exchange['keyFile'])

    def start_engine(self):
        logging.info('Starting Triangular Arbitrage Engine...')
        if self.mock:
            logging.info('---------------------------- MOCK MODE ----------------------------')
        #Send the request asynchronously
        while True:
#             try:
                if not self.mock and self.hasOpenOrder:
                    self.check_openOrder()
                elif self.check_balance():           
                    bookStatus = self.check_orderBook()
                    if bookStatus['status']:
                        self.place_order(bookStatus['orderInfo'])
#             except Exception, e:
#                 # raise
#                 print e
            
                time.sleep(self.engine.sleepTime)
    
    def check_openOrder(self):
        if self.openOrderCheckCount >= 5:
            self.cancel_allOrders()
        else:
            logging.info('checking open orders...')
            rs = [self.engine.get_open_order()]
            responses = self.send_request(rs)

            if not responses[0]:
                logging.info(responses)
                return False
            
            if responses[0].parsed:
                self.engine.openOrders = responses[0].parsed
                logging.info(self.engine.openOrders)
                self.openOrderCheckCount += 1
            else:
                self.hasOpenOrder = False
                logging.info('no open orders')
    
    def cancel_allOrders(self):
        logging.info('cancelling all open orders...')
        rs = []
        logging.debug(self.exchange['exchange'])
        for order in self.engine.openOrders:
            logging.debug(order)
            rs.append(self.engine.cancel_order(order['orderId']))

        responses = self.send_request(rs)
        
        self.engine.openOrders = []
        self.hasOpenOrder = False
        

    #Check and set current balance
    def check_balance(self):
        rs = [self.engine.get_balance([
            self.exchange['tickerA'],
            self.exchange['tickerB'],
            self.exchange['tickerC']
            ])]

        responses = self.send_request(rs)

        self.engine.balance = responses[0].parsed

        ''' Not needed? '''
        # if not self.mock:
        #     for res in responses:
        #         for ticker in res.parsed:
        #             if res.parsed[ticker] < 0.05:
        #                 print ticker, res.parsed[ticker], '- Not Enough'
        #                 return False
        return True
    
    def check_orderBook(self):
        logging.info('starting to check order book...')

        rs = [self.engine.get_ticker_lastPrice(self.exchange['tickerA']),
            self.engine.get_ticker_lastPrice(self.exchange['tickerB']),
            self.engine.get_ticker_lastPrice(self.exchange['tickerC']),
        ]
        lastPrices = []
        rs_values = self.send_request(rs)
        logging.debug("Found {} results".format(len(rs_values)))
        for res in rs_values:
            for key in res.parsed:
                logging.info('{} = {}USD'.format(key, res.parsed[key]))
            lastPrices.append(next(res.parsed.itervalues()))

        rs = [self.engine.get_ticker_orderBook_innermost(self.exchange['tickerPairA']),
              self.engine.get_ticker_orderBook_innermost(self.exchange['tickerPairB']),
              self.engine.get_ticker_orderBook_innermost(self.exchange['tickerPairC']),
              ]

        responses = self.send_request(rs)
        
#         if self.mock:
        logging.info('{0} - {1}; {2} - {3}; {4} - {5}'.format(
            self.exchange['tickerPairA'],
            responses[0].parsed,
            self.exchange['tickerPairB'],
            responses[1].parsed,
            self.exchange['tickerPairC'],
            responses[2].parsed
            ))
        
        # bid route BTC->ETH->LTC->BTC
        bidRoute_result = (1 / responses[0].parsed['ask']['price']) \
                            / responses[1].parsed['ask']['price']   \
                            * responses[2].parsed['bid']['price']  
        # ask route ETH->BTC->LTC->ETH
        askRoute_result = (1 * responses[0].parsed['bid']['price']) \
                            / responses[2].parsed['ask']['price']   \
                            * responses[1].parsed['bid']['price']

        logging.info('Bid Route: {} Ask Route: {}'.format(bidRoute_result, askRoute_result))

        # Max amount for bid route & ask routes can be different and so less profit
        if bidRoute_result > 1 or \
        (bidRoute_result > 1 and askRoute_result > 1 and (bidRoute_result - 1) * lastPrices[0] > (askRoute_result - 1) * lastPrices[1]):
            status = 1 # bid route
        elif askRoute_result > 1:
            status = 2 # ask route
        else:
            status = 0 # do nothing

        if status > 0:
            maxAmounts = self.getMaxAmount(lastPrices, responses, status)
            logging.info('Max Amounts: {}'.format(maxAmounts))
            fee = 0
            for index, amount in enumerate(maxAmounts):
                fee += amount * lastPrices[index]
            fee *= self.engine.feeRatio

            logging.info('Max Amounts: {}\nFee: {}'.format(maxAmounts, fee))
            
            bidRoute_profit = (bidRoute_result - 1) * lastPrices[0] * maxAmounts[0]
            askRoute_profit = (askRoute_result - 1) * lastPrices[1] * maxAmounts[1]
            # print 'bidRoute_profit - {0} askRoute_profit - {1} fee - {2}'.format(
            #     bidRoute_profit, askRoute_profit, fee
            # )
            if status == 1 and bidRoute_profit - fee > self.minProfitUSDT:
                logging.info(' Bid Route: Result - {0} Profit - {1} Fee - {2}'.format(bidRoute_result, bidRoute_profit, fee))
                orderInfo = [
                    {
                        "tickerPair": self.exchange['tickerPairA'],
                        "action": "bid",
                        "price": responses[0].parsed['ask']['price'],
                        "amount": maxAmounts[0]
                    },
                    {
                        "tickerPair": self.exchange['tickerPairB'],
                        "action": "bid",
                        "price": responses[1].parsed['ask']['price'],
                        "amount": maxAmounts[1]
                    },
                    {
                        "tickerPair": self.exchange['tickerPairC'],
                        "action": "ask",
                        "price": responses[2].parsed['bid']['price'],
                        "amount": maxAmounts[2]
                    }                                        
                ]
                return {'status': 1, "orderInfo": orderInfo}
            elif status == 2 and askRoute_profit - fee > self.minProfitUSDT:
                logging.info(' Ask Route: Result - {0} Profit - {1} Fee - {2}'.format(askRoute_result, askRoute_profit, fee))
                orderInfo = [
                    {
                        "tickerPair": self.exchange['tickerPairA'],
                        "action": "ask",
                        "price": responses[0].parsed['bid']['price'],
                        "amount": maxAmounts[0]
                    },
                    {
                        "tickerPair": self.exchange['tickerPairB'],
                        "action": "ask",
                        "price": responses[1].parsed['bid']['price'],
                        "amount": maxAmounts[1]
                    },
                    {
                        "tickerPair": self.exchange['tickerPairC'],
                        "action": "bid",
                        "price": responses[2].parsed['ask']['price'],
                        "amount": maxAmounts[2]
                    }                                        
                ]               
                return {'status': 2, 'orderInfo': orderInfo}
        else:
            logging.info("No interesting route found. Doing nothing.")
    
        logging.debug("check order book end")
        return {'status': 0}

    # Using USDT may not be accurate
    def getMaxAmount(self, lastPrices, orderBookRes, status):
        maxUSDT = []
        for index, tickerIndex in enumerate(['tickerA', 'tickerB', 'tickerC']):
            # 1: 'bid', -1: 'ask'
            if index == 0: bid_ask = -1
            elif index == 1: bid_ask = -1
            else: bid_ask = 1
            # switch for ask route
            if status == 2: bid_ask *= -1
            bid_ask = 'bid' if bid_ask == 1 else 'ask'
            
            maxBalance = min(orderBookRes[index].parsed[bid_ask]['amount'], self.engine.balance[self.exchange[tickerIndex]])
            # print '{0} orderBookAmount - {1} ownAmount - {2}'.format(
            #     self.exchange[tickerIndex], 
            #     orderBookRes[index].parsed[bid_ask]['amount'], 
            #     self.engine.balance[self.exchange[tickerIndex]]
            # )
            USDT = maxBalance * lastPrices[index] * (1 - self.engine.feeRatio)
            if not maxUSDT or USDT < maxUSDT: 
                maxUSDT = USDT       

        maxAmounts = []
        for index, tickerIndex in enumerate(['tickerA', 'tickerB', 'tickerC']):
            # May need to handle scientific notation
            maxAmounts.append(maxUSDT / lastPrices[index])

        return maxAmounts

    def place_order(self, orderInfo):
        logging.debug(orderInfo)
        rs = []
        for order in orderInfo:
            rs.append(self.engine.place_order(
                order['tickerPair'],
                order['action'],
                order['amount'],
                order['price'])
            )

        if not self.mock:
            responses = self.send_request(rs)

        self.hasOpenOrder = True
        self.openOrderCheckCount = 0

    def send_request(self, rs):
        responses = grequests.map(rs)
        for res in responses:
            if not res:
                logging.info(responses)
                raise Exception
        return responses

    def run(self):
        self.start_engine()

if __name__ == '__main__':
    exchange = {
        'exchange': 'bittrex',
        'keyFile': '../keys/bittrex.key',
        'tickerPairA': 'BTC-ETH',
        'tickerPairB': 'ETH-LTC',
        'tickerPairC': 'BTC-LTC',
        'tickerA': 'BTC',
        'tickerB': 'ETH',
        'tickerC': 'LTC'
    }    
    engine = CryptoEngineTriArbitrage(exchange, True)
    #engine = CryptoEngineTriArbitrage(exchange)
    engine.run()
