'''
Created on Aug 19, 2018

@author: afm
'''
import grequests
import unittest
from mock import patch
import mock
import logging

# from engines.triangular_arbitrage import CryptoEngineTriArbitrage
import engines
import engines.exchanges.bittrex 
import engines.triangular_arbitrage
from mock.mock import _side_effect_methods

'''
request:
str: https://bittrex.com/api/v1.1/account/getbalances?apikey=c2e105480b7a4bf785f4e6169bd841ca&nonce=1535812611558

response:
str: 
{
"success":true,
"message":"",
"result":[
        {
            "Currency":"BCH",
            "Balance":0.00100000,
            "Available":0.00100000,
            "Pending":0.00000000,
            "CryptoAddress":"14nXPSydUCJnqLFSboXRXdz49PkyB4FS3A"
        },
        {"Currency":"BTC","Balance":0.09368291,"Available":0.09368291,"Pending":0.00000000,"CryptoAddress":null},
        {"Currency":"ETH","Balance":0.00000194,"Available":0.00000194,"Pending":0.00000000,"CryptoAddress":"0x01a2d435698f5ac911c5316a90e0ff6220027de3"},
        {"Currency":"PTOY","Balance":113.36108244,"Available":113.36108244,"Pending":0.00000000,"CryptoAddress":null}
    ]
}

request:
str: https://bittrex.com/api/v1.1/public/getticker?market=USDT-BTC

response: _content
str: 
{
    "success":true,
    "message":"",
    "result":{
        "Bid":7075.34566868,
        "Ask":7083.38999999,
        "Last":7083.38900000
    }
}

request:
url    str: https://bittrex.com/api/v1.1/public/getorderbook?type=both&market=BTC-ETH    


response:
_content    str: {
    "success":true,
    "message":"","result":{"buy":[{"Quantity":2.93260000,"Rate":0.04065854},{"Quantity":1.91109525,"Rate":0.04065254},{"Quantity":0.30403250,"Rate":0.04065107},{"Quantity":7.25692853,"Rate":0.04065106},{"Quantity":111.60468394,"Rate":0.04064904},{"Quantity":1.41700000,"Rate":0.04064137},{"Quantity":1.76000000,"Rate":0.04063937},{"Quantity":2.65500000,"Rate":0.04063139},{"Quantity":2.96200000,"Rate":0.04062140},{"Quantity":2.56800000,"Rate":0.04061440},{"Quantity":4.72585000,"Rate":0.04056400},{"Quantity":0.05000000,"Rate":0.04056201},{"Quantity":0.40300000,"Rate":0.04055100},{"Quantity":0.47600000,"Rate":0.04054900},{"Quantity":0.29000000,"Rate":0.04052804},{"Quantity":60.35438533,"Rate":0.04052803},{"Quantity":0.02702398,"Rate":0.04051964},{"Quantity":4.54000000,"Rate":0.04051949},{"Quantity":0.53300000,"Rate":0.04051939},{"Quantity":17.67938830,"Rate":0.04050976},{"Quantity":2.12206985,"Rate":0.04050022},{"Quantity":0.24694492,"Rate":0.04049486},{"Quantity":27.249273...    

'''

bittrex_getbalances_result = {  
   u'message':u'',
   u'result':[  
      {  
         u'Available':0.001,
         u'Currency':u'BCH',
         u'Balance':0.001,
         u'Pending':0.0,
         u'CryptoAddress':u'14nXPSydUCJnqLFSboXRXdz49PkyB4FS3A'
      },
      {  
         u'Available':0.09368291,
         u'Currency':u'BTC',
         u'Balance':0.09368291,
         u'Pending':0.0,
         u'CryptoAddress':None
      },
      {  
         u'Available':1.94e-06,
         u'Currency':u'ETH',
         u'Balance':1.94e-06,
         u'Pending':0.0,
         u'CryptoAddress':u'0x01a2d435698f5ac911c5316a90e0ff6220027de3'
      },
      {  
         u'Available':999,
         u'Currency':u'PTOY',
         u'Balance':999,
         u'Pending':0.0,
         u'CryptoAddress':None
      }
   ],
   u'success':True
}

config = {
    "triangular": {
        "exchange": "bittrex",
        "keyFile": "keys/bittrex.key",
        "tickerPairA": "BTC-ETH",
        "tickerPairB": "ETH-LTC",
        "tickerPairC": "BTC-LTC",
        "tickerA": "BTC",
        "tickerB": "ETH",
        "tickerC": "LTC",
        "minProfitUSDT" : "0.3"
    },
    "exchange": {
        "minProfit": "0.00005",
        
        "exchangeA": {
            "exchange": "bittrex",
            "keyFile": "keys/bittrex.key",
            "tickerPair": "BTC-ETH",
            "tickerA": "BTC",
            "tickerB": "ETH"        
        },
        "exchangeB": {
            "exchange": "bitstamp",
            "keyFile": "keys/bitstamp.key",
            "tickerPair": "ethbtc",
            "tickerA": "BTC",
            "tickerB": "ETH"         
        }
    }
}

def mock__send_request(command, httpMethod, params={}, hook=None):
    '''
    This method doesn't actually send the request: it produces and returns
    a grequests object which should then be passed to grequests.map which will
    process it and make the actual connection to get the results.
    '''
    import time
    # Connection Timeout. If Bittrex takes to long to reply, just timeout.
    params['timeout']=10
    
    command = '/{0}/{1}'.format('v1.1', command)

    API_URL = 'https://bittrex.com/api'
    url = API_URL + command
    
    if httpMethod == "GET":
        R = grequests.get
    elif httpMethod == "POST":
        R = grequests.post       
    
    headers = {}
    
    if not any(x in command for x in ['Public', 'public']):
        nonce = str(int(1000*time.time()))
        url = url + '{0}apikey={1}&nonce={2}'.format('&' if '?' in url else '?', self.key['public'], nonce)
        
        secret = self.key['private']
        
        signature = hmac.new(secret.encode('utf8'), url.encode('utf8'), hashlib.sha512)
        signature = signature.hexdigest()
        
        headers = {
            'apisign': signature,
        }        

    args = params
    args['headers'] = headers #add headers with apisign to request arguments

    if hook:
        args['hooks'] = dict(response=hook)
        
    req = R(url, **args)
    
    if self.async:
        return req
    else:
        response = grequests.map([req])[0].json()
        
        if 'error' in response:
            logging.info(response)
        return response


def mock_get_balance(self, tickers=[]):
    logging.warn("Mocking get Balances")
    balance=self._send_request('account/getbalances', 'GET', {}, [mock_hook_getBalance(tickers=tickers)])
    logging.debug(balance.kwargs)
    return balance


def mock_hook_getBalance(*factory_args, **factory_kwargs):
    def res_hook(r, *r_args, **r_kwargs):
        json = bittrex_getbalances_result
        logging.debug(json)
        r.parsed = {}
        

        if factory_kwargs['tickers']:
            json['result'] = filter(lambda ticker: ticker['Currency'].upper() in factory_kwargs['tickers'], json['result'])
            
        for ticker in json['result']:
            r.parsed[ticker['Currency'].upper()] = float(ticker['Available'])
                              
    return res_hook    

def mock_send_request(self, rs):
    logging.info("WARNING: Running Mock Send Requests.")
    responses = grequests.map(rs)
    for res in responses:
        if not res:
            logging.error(responses)
            raise Exception
    logging.debug(responses)
    return responses


class Test(unittest.TestCase):


    def setUp(self):
        import json
        configFile = 'arbitrage_config.json'
        f = open(configFile)    
        self.config = json.load(f)
        f.close()
        self.config['isMockMode'] = False
        self.config['logdata']    = '/tmp/triangular.log'
        logging.basicConfig(format='%(asctime)s - %(levelname)s - %(pathname)s:%(funcName)s(): %(message)s',
                    level=logging.DEBUG)



    def tearDown(self):
        pass

    @unittest.skip("Disabled")
    def testOne(self):
        logging.warn("Running Test One Warn")
        logging.warning("Running Test One Warning")
#         class ExchangeEngine(engines.exchanges.bittrex.ExchangeEngine):
#             hook_getBalance = mock_hook_getBalance
             
#         engines.exchanges.bittrex.ExchangeEngine.get_balance = mock_get_balance
#         engines.exchanges.bittrex.ExchangeEngine.__dict__["get_balance"] = mock_get_balance
         
#         engines.triangular_arbitrage.CryptoEngineTriArbitrage.send_request = mock_send_request
        bittrex_engine = engines.triangular_arbitrage.CryptoEngineTriArbitrage(self.config)
        bittrex_engine.engine.get_balance = mock_get_balance
        
        bittrex_engine.run()
        
    @unittest.skip("Disabled")
    def testTwo(self):
        def mock_run(obj=None):
            print('I Ran allright.')
        
#         CryptoEngineTriArbitrage.__dict__["run"] = mock_run()
        engines.triangular_arbitrage.CryptoEngineTriArbitrage.run = mock_run
        engine = engines.triangular_arbitrage.CryptoEngineTriArbitrage(self.config)
        
#         engine.run = mock_run
        
        engine.run()
        
        
#     @unittest.skip("Disabled")    
    @patch('engines.triangular_arbitrage.CryptoEngineTriArbitrage.engine.get_balance', 
           side_effect=mock_get_balance)
    def testMocks(self, MockCryptoEngineTriArbitrage):
        mock_ceta = MockCryptoEngineTriArbitrage(config)
        
#         mock_ceta.get_balance = 'I Ran allright.'
        
#         r = run()
        r = mock_ceta.run()
        
        print("{}".format(r))

#     @unittest.skip("Disabled")
    def testBittrexAPI(self):
        import grequests
        bte = engines.exchanges.bittrex.ExchangeEngine()
        bte.load_key('./keys/bittrex.key')
        get_balances_request = bte.get_balance()
        
        logging.debug('request URL is: {}'.format(get_balances_request.url))
        resp = grequests.map([get_balances_request])
        self.assertEqual(resp[0].status_code, 200, "HTTP Status Code NOT 200. Something went wrong.")
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()