#!/bin/bash

# Import csv data into PostgreSQL
# Then spits out only lines which have a route greater than 1 into another CSV.

CSVFILE="/home/fb2155/public_html/ca_logdata.csv"
TRIROOT="${HOME}/public_html/nadira/triangular/"
CSVTEMP="${TRIROOT}/ca_logdata.importing"
CSVABOVE="${TRIROOT}/ca_logdata_above.csv"

grep , ${CSVFILE} > ${CSVTEMP} && rm ${CSVFILE}

cat << ENDEND | psql 
CREATE TABLE crypto_arbitrage_triangular (
date timestamp,
tickerA	char(3),
tickerPairA_ask_price numeric,
tickerPairA_bid_price numeric,
tickerB char(3),
tickerPairB_ask_price numeric,
tickerPairB_bid_price numeric,
tickerC	char(3),
tickerPairC_ask_price numeric,
tickerPairC_bid_price nu meric,
bidRoute_result	numeric,
askRoute_result numeric,
ricavo_potenziale_bid_tickerA numeric,
ricavo_potenziale_ask_tickerB numeric);											
ENDEND

cat << ENDENDEND | psql
\copy crypto_arbitrage_triangular FROM '${CSVTEMP}' WITH (FORMAT CSV);
ENDENDEND

cat << ENDENDEND | psql
\copy (SELECT * FROM crypto_arbitrage_triangular WHERE askroute_result >= 1 OR bidroute_result >= 1) TO '${CSVABOVE}' WITH (FORMAT csv);
ENDENDEND

