'''
Created on Aug 19, 2018

@author: afm
'''
import unittest
import engines


class Test(unittest.TestCase):


    def setUp(self):
        import json
        configFile = 'arbitrage_config.json'
        f = open(configFile)    
        self.config = json.load(f)
        f.close()
        self.config['isMockMode'] = False
        self.config['logdata']    = '/tmp/triangular.log'



    def tearDown(self):
        pass


    def testOne(self):
        engine = engines.triangular_arbitrage.CryptoEngineTriArbitrage(self.config)



if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()