import argparse
import json
import logging

configFile = 'arbitrage_config.json'

f = open(configFile)    
config = json.load(f)
f.close()

pretty_config_triangular  = 'Running Triangular on exchange {exchange} between {tickerPairA}, {tickerPairB} and {tickerPairC}\nUsing keys in {keyFile}'.format(**config['triangular'])
pretty_config_arbitrage =  ''

parser = argparse.ArgumentParser(description='Crypto Arbitrage')
parser.add_argument('-m', '--mode', 
                    help='Arbitrage mode: triangular or exchange', 
                    required=True)
parser.add_argument('-p', '--production', 
                    help='Production mode', 
                    action='store_true')
parser.add_argument('-l', '--loglevel', 
                    help='Allowed log levels: CRITICAL, ERROR, WARNING, INFO, DEBUG', 
                    default=logging.INFO)
parser.add_argument('-o', '--logdata',
                    help='Write data from market related to how to make a decision to \
                    a file') 

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(funcName)s: %(message)s',
                    level=args.loglevel)

engine = None
# isMockMode = True if not args.production else False
config['isMockMode'] = not args.production

if args.mode == 'triangular':
    logging.info(pretty_config_triangular)
    from engines.triangular_arbitrage import CryptoEngineTriArbitrage
    engine = CryptoEngineTriArbitrage(config)
elif args.mode == 'exchange':
    logging.info(pretty_config_arbitrage)
    from engines.exchange_arbitrage import CryptoEngineExArbitrage
    engine = CryptoEngineExArbitrage(config['exchange'])
else:
    print 'Mode {0} is not recognized'.format(args.mode)

if engine:
    engine.run()
