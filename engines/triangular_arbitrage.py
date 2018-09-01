'''
* The code tries two ways of making a profit via arbitrage. It doesn't just 
    check if A > B > C > A makes a profit, but also tries B > A > C > B, and 
    compares the two routes, to see which one is more profitable. 
* One route is called "Bid" route, because from the initial currency A, it 
    places a bid to purchase B. Start by selling A.
* The other route is called "ask", because it asks to buy more currency A to 
    start with. Start by buying A.
* The gain is then calculated for each route: if it's > 1, there is a gain, if 
    it's < 1, there is a loss.
* The gains of both routes are compared: the largest positive gain is chosen.
'''

import csv, datetime
import time
import grequests
from exchanges.loader import EngineLoader
import logging

LOG_LEVEL=logging.DEBUG

STATUS_DO_NOTHING = 0
STATUS_BID_ROUTE = 1
STATUS_ASK_ROUTE = 2

tickerA = ""
tickerB = ""
tickerC = ""


class CryptoEngineTriArbitrage(object):

    def __init__(self, config):
        self.exchange = config['triangular']
        self.mock    = config['isMockMode'] 
        self.logdata = config['logdata']
        self.minProfitUSDT = float(self.exchange['minProfitUSDT'])
        self.hasOpenOrder = True # always assume there are open orders first
        self.openOrderCheckCount = 0
        
        self.logdataline = []

        global tickerA, tickerB, tickerC
        tickerA = self.exchange['tickerA']
        tickerB = self.exchange['tickerB']
        tickerC = self.exchange['tickerC']
        
        self.engine = EngineLoader.getEngine(self.exchange['exchange'], self.exchange['keyFile'])

    def start_engine(self):
        logging.info('Starting Triangular Arbitrage Engine...')
        if self.mock:
            logging.info('---------------------------- MOCK MODE ----------------------------')
        #Send the request asynchronously
        while True:
#             try:
            self.logdataline = []
            self.logdataline.append(datetime.datetime.utcnow())

            if not self.mock and self.hasOpenOrder:
                self.check_openOrder()
            elif self.check_balance():           
                bookStatus = self.check_orderBook()
                if bookStatus['status']:
                    self.place_order(bookStatus['orderInfo'])
            if self.logdata is not None:
                with open(self.logdata,'a') as logdatafile:
                    w = csv.writer(logdatafile, quotechar='"', quoting=csv.QUOTE_ALL) 
                    w.writerow(self.logdataline)
                    
#             except Exception, e:
#                 # raise
#                 print e
            
                time.sleep(self.engine.sleepTime + 10)
    
    def check_openOrder(self):
        if self.openOrderCheckCount >= 5:
            self.cancel_allOrders()
        else:
            logging.info('checking open orders...')
            rs = [self.engine.get_open_order()]
            responses = self.send_request(rs)

            if not responses[0]:
                # No responses
                logging.error(responses)
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
            logging.debug("Adding {} to list of orders to cancel.".format(order['orderId']))
            rs.append(self.engine.cancel_order(order['orderId']))

        responses = self.send_request(rs)
        
        self.engine.openOrders = []
        self.hasOpenOrder = False
        

    #Check and set current balance
    def check_balance(self):
        
        not_enough = False
        
        rs = [self.engine.get_balance([tickerA,tickerB,tickerC])] 

        logging.info("Fetching balances for all non-zero wallets.")
        responses = self.send_request(rs)

        import json
        rc = json.loads(responses[0]._content)
        for result in rc['result']:
            logging.debug("Found Wallet with {} {}".format(result['Currency'], result['Balance']))

        self.engine.balance = responses[0].parsed
        logging.debug(self.engine.balance)
        
        if ((tickerA not in self.engine.balance)  or 
            (self.engine.balance[tickerA] <= 0.0) ):
            logging.warn("{} wallet inexistant or with zero balance. Can't continue.".format(tickerA))
            not_enough = True
        if ((tickerB not in self.engine.balance)  or 
            (self.engine.balance[tickerB] <= 0.0) ):
            logging.warn("{} wallet inexistant or with zero balance. Can't continue.".format(tickerB))
            not_enough = True
        if ((tickerC not in self.engine.balance)  or 
            (self.engine.balance[tickerC] <= 0.0) ):
            logging.warn("{} wallet inexistant or with zero balance. Can't continue.".format(tickerC))
            not_enough = True

        
        ''' Not needed? '''
        for res in responses:
            for ticker in res.parsed:
                at_least = 0.0
                if res.parsed[ticker] < at_least:
                    logging.warning("{0} {1} - Not Enough. At least {2} {0} is required.".format(ticker, res.parsed[ticker], at_least))
                    not_enough = True
                    
        if not_enough == True: 
            return False
        else:
            logging.info("Found enough currency in all wallets. Proceeding.")
            return True
    
    def check_orderBook(self):
        logging.info('starting to check order book...')

        # Create AsyncRequest to then feed into send_request
        rs = [self.engine.get_ticker_lastPrice(tickerA),
            self.engine.get_ticker_lastPrice(tickerB),
            self.engine.get_ticker_lastPrice(tickerC),
        ]
        lastPrices = []
        
        # Get last price of each ticker
        logging.debug("Fetching lastPrices...")
        rs_values = self.send_request(rs)
#         logging.debug("Found {} results".format(len(rs_values)))
        for res in rs_values:
            for key in res.parsed:
                logging.info('lastPrices: {} = {}USD'.format(key, res.parsed[key]))
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
        
        '''
        tickerPairA = tickerA-tickerB (units in tickerA)
        tickerPairB = tickerB-tickerC (units in tickerB)
        tickerPairC = tickerA-tickerC (units in tickerA)
        
        bidRoute_result and askRoute_result are 1.0 in a perfect, ideal, 
            efficient market.
            
        bidRoute_result and askRoute_result > 1.0 means inefficencies in market
            which can be exploited to make a profit.
                    
        '''
        tickerPairA_ask_price = responses[0].parsed['ask']['price']
        tickerPairA_bid_price = responses[0].parsed['bid']['price']
        tickerPairB_ask_price = responses[1].parsed['ask']['price']
        tickerPairB_bid_price = responses[1].parsed['bid']['price']
        tickerPairC_ask_price = responses[2].parsed['ask']['price']
        tickerPairC_bid_price = responses[2].parsed['bid']['price']
        
        self.logdataline.append(tickerA)
        self.logdataline.append(tickerPairA_ask_price)
        self.logdataline.append(tickerPairA_bid_price)
        
        self.logdataline.append(tickerB)
        self.logdataline.append(tickerPairB_ask_price)
        self.logdataline.append(tickerPairB_bid_price)

        self.logdataline.append(tickerC)
        self.logdataline.append(tickerPairC_ask_price)
        self.logdataline.append(tickerPairC_bid_price)
        
        # Calculate the gain factor for each route
        
        # bid route tickerA->tickerB->tickerC->tickerA
        bidRoute_result = (1 / tickerPairA_ask_price) / tickerPairB_ask_price * tickerPairC_bid_price
        # ask route tickerB->tickerA->tickerC->tickerB
        askRoute_result = tickerPairA_bid_price / tickerPairC_ask_price * tickerPairB_bid_price

        self.logdataline.append(bidRoute_result)
        self.logdataline.append(askRoute_result)
                            
#         # bid route tickerA->tickerB->tickerC->tickerA
#         bidRoute_result = (1 / responses[0].parsed['ask']['price']) \
#                             / responses[1].parsed['ask']['price']   \
#                             * responses[2].parsed['bid']['price']  
#         # ask route tickerB->tickerA->tickerC->tickerB
#         askRoute_result = (1 * responses[0].parsed['bid']['price']) \
#                             / responses[2].parsed['ask']['price']   \
#                             * responses[1].parsed['bid']['price']

        logging.info('Bid Route: {} Ask Route: {}'.format(bidRoute_result, askRoute_result))

        # Calculate the actual real monetary gain in USD for each route
        ricavo_potenziale_bid_tickerA = (bidRoute_result - 1) * lastPrices[0] # units in USDT
        ricavo_potenziale_ask_tickerB = (askRoute_result - 1) * lastPrices[1] # units in USDT
        
        self.logdataline.append(ricavo_potenziale_bid_tickerA)
        self.logdataline.append(ricavo_potenziale_ask_tickerB)
        
        # Compare the real monetary gains for each route with each other,
        # and select route with highest gain. 
        if (ricavo_potenziale_bid_tickerA > ricavo_potenziale_ask_tickerB) and \
            ricavo_potenziale_bid_tickerA > 0:
            # If we can make more money going for the bid route, let's do it.
            status = STATUS_BID_ROUTE
        elif (ricavo_potenziale_ask_tickerB > ricavo_potenziale_bid_tickerA) and \
            ricavo_potenziale_ask_tickerB > 0:
            # If we can make more money going for the ask route, let's do it.
            status = STATUS_ASK_ROUTE
        else:
            # If we would loose money, don't do it (two of spades).
            status = STATUS_DO_NOTHING
        
        # Max amount for bid route & ask routes can be different and so less profit
#         if bidRoute_result > 1 or \
#             (askRoute_result > 1 and 
#              ricavo_potenziale_bid_tickerA > ricavo_potenziale_ask_tickerB) :
#         #(bidRoute_result > 1 and askRoute_result > 1 and (bidRoute_result - 1) * lastPrices[0] > (askRoute_result - 1) * lastPrices[1]):
#             status = STATUS_BID_ROUTE
#         elif askRoute_result > 1:
#             status = STATUS_ASK_ROUTE
#         else:
#             status = STATUS_DO_NOTHING

#         status = STATUS_BID_ROUTE

        if status > STATUS_DO_NOTHING:
            logging.info('Found possible possibility to make some gains. Status = {}'.format(status))
            maxAmounts = self.getMaxAmount(lastPrices, responses, status)
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
            if status == STATUS_BID_ROUTE and bidRoute_profit - fee > self.minProfitUSDT:
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
                return {'status': STATUS_BID_ROUTE, "orderInfo": orderInfo}
            elif status == STATUS_ASK_ROUTE and askRoute_profit - fee > self.minProfitUSDT:
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
            logging.info("No interesting route found. Two of Spades.")
    
        logging.debug("check order book end")
        return {'status': 0}

    '''
    orderBookRes: Responses from HTTP queries to order book. It's a list, on 
                  item per ticker. We need it here only to get the 
                  parsed[ask|bid][amount] value for each currency. 
                  
    status:       Indicates 
    '''
    # Using USDT may not be accurate
    def getMaxAmount(self, lastPrices, orderBookRes, status):
        maxUSDT = []
        BID = 1
        ASK = -1
        for index, tickerIndex in enumerate(['tickerA', 'tickerB', 'tickerC']):
            # 1: 'bid', -1: 'ask'
            if tickerIndex == 'tickerA': bid_ask = ASK
            elif tickerIndex == 'tickerB': bid_ask = ASK
            else: bid_ask = BID

#             if index == 0: bid_ask = -1
#             elif index == 1: bid_ask = -1
#             else: bid_ask = 1

            # switch for ask route
            if status == STATUS_ASK_ROUTE: bid_ask *= -1

            bid_ask = 'bid' if bid_ask == 1 else 'ask'
            
            logging.info('Ticker: {} Route decided: {}'.format(tickerIndex, bid_ask))
            
            logging.debug(self.engine.balance[self.exchange[tickerIndex]])
            
            maxBalance = min(orderBookRes[index].parsed[bid_ask]['amount'], 
                             self.engine.balance[self.exchange[tickerIndex]])
            
            logging.debug('{0} - orderBookAmount: {1}; ownAmount: {2}'.format(
                self.exchange[tickerIndex], 
                orderBookRes[index].parsed[bid_ask]['amount'], 
                self.engine.balance[self.exchange[tickerIndex]]
            ))
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
                logging.error(responses)
                raise Exception
        logging.debug(responses)
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
        'tickerC': 'PTOY'
    }    
    engine = CryptoEngineTriArbitrage(exchange, True)
    #engine = CryptoEngineTriArbitrage(exchange)
    engine.run()
