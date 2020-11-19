''' Custom Robinhood processes 
    + All custom functions interacting with RH package
    + Built on top of "robin_stocks" package
        - documentation: https://robin-stocks.readthedocs.io/en/latest/functions.html
    + Primarily used to send transaction to RH and for basic account info
    + For options and cryptos, use other brokers
        - Listed options take 60+ seconds to retrieve
        - There are better brokers/exchanges for crypto
'''

#%% Import packages      
import os, sys
import config as config

import datetime as dt
import pandas as pd
import robin_stocks as r
import time

#%% Now time
def now():
    'Return now time, cleanly formatted'
    datetime = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return datetime

#%% Connect to Robinhood application
class app:
    ''' Robinhood connection-type processes
    '''
    # initialize login information
    def __init__(self, user_info=config.user_info):
        'Login with info provided in config.py file'
        self.rh_user = user_info['robinhood']['username']
        self.rh_pw = user_info['robinhood']['password']

    # Connect to to Robinhood
    def connect_robinhood(self):
        r.login(username=self.rh_user, password=self.rh_pw)        

#%% Account information
class account:
    ''' Routine processes for handling account infomation
        + holdings, buying power, etc.
    '''
    # Open positions
    class get_position:
        ''' Return df of open positions in individual or aggregate asset classes.
            + my_holdings() --- aggregate
        '''
        def buying_power():
            'not in use -- delete'
            account_profile = r.profiles.load_account_profile()
            buying_power = float(account_profile['buying_power'])
            return buying_power

        def equity():
            # Fetch positions from RH
            positions = r.account.build_holdings()     

            # Open stock positions
            result = [positions[p] for p in positions]
            result = pd.DataFrame(result)
            result.insert(0,'symbol',positions.keys())
            result = result.sort_values(by='symbol').reset_index(drop=True)
            return result

        def options():
            # Fetch positions from RH
            positions = r.options.get_open_option_positions()         # open options position
            
            # Open options positions
            result = pd.DataFrame(positions)
            result = result.set_index('chain_symbol').reset_index()   # workaround for moving chain_symbol to first column
            result = result.sort_values(by='chain_symbol').reset_index(drop=True)

            # Mkt quote of position        
            mkt_quote = r.options.get_option_market_data_by_id(id=result.option_id[0])        # get mkt data for specific option
            mkt_quote = pd.DataFrame([mkt_quote])            
            return result, mkt_quote

        def crypto():
            # Fetch positions form RH
            positions = r.crypto.get_crypto_positions()
            
            # Open crypto positions
            symbols = [x['currency']['code'] for x in positions]
            result = pd.DataFrame(positions)
            result.insert(0,'symbol', symbols)
            result = result.sort_values(by='symbol').reset_index(drop=True)
        
            # Mkt quote of position
            mkt_quote = [r.crypto.get_crypto_quote(symbol=s) for s in result.symbol]
            mkt_quote = pd.DataFrame(mkt_quote)

            return result, mkt_quote

        def my_holdings():
            'Return df of open positions, all asset class'        
            portfolio_value = float(r.account.build_user_profile()['equity'])

            def equity():
                equities = account.get_position.equity()            # custom function
                cost = equities.average_buy_price.astype(float)
                price = equities.price.astype(float)
                quantity = equities.quantity.astype(float)
                result = {
                    'symbol':equities.symbol,
                    'price':price,
                    'quantity':quantity,
                    'pct_change':equities.percent_change.astype(float),
                    'inst':'equity',
                    'cost':cost,
                    'pos_$':equities.equity.astype(float),
                    'pos_%':(equities.equity.astype(float) / portfolio_value)*100,
                    'r_$':price - cost,
                    'r_%':(price / cost - 1) * 100,
                }
                result = pd.DataFrame(result).sort_values(by='symbol')
                return result
            
            def options():
                options, mkt_quote = account.get_position.options()
                price = mkt_quote.adjusted_mark_price.astype(float)     # price per shae
                cost = options.average_price.astype(float) / 100        # cost per share
                quantity = options.quantity.astype(float)

                # Get options detail
                option_id = options.option_id
                option_side = options.type
                option_type, option_strike = [], []
                
                # Get option inst
                for x in option_id:
                    detail = r.options.get_option_instrument_data_by_id(x)
                    option_type.append(detail['type'])
                    option_strike.append(float(detail['strike_price']))
                option_detail = {
                    'option_strike':option_strike,
                    'option_side': option_side,
                    'option_type': option_type,
                }
                inst = []
                for x, strike in enumerate(option_detail['option_strike']):
                    inst.append(
                        '{strike} {side}{type}'.format(
                            strike=int(strike),
                            side=option_detail['option_side'][x][0],
                            type=option_detail['option_type'][x][0].upper(),
                        )
                    )

                # Results
                result = {
                    'symbol':options.chain_symbol,
                    'inst':inst,                   # call / put options
                    'price':price,
                    'pct_change':(price / mkt_quote.previous_close_price.astype(float) - 1) * 100,
                    'quantity':quantity,
                    'pos_$':price * 100 * quantity,
                    'pos_%':((price * 100 * quantity) / portfolio_value) * 100,
                    'r_$':(price - cost)*100 * quantity,
                    'r_%':(price / cost - 1) * 100,
                    'cost': cost,
                }
                result = pd.DataFrame(result)
                return result

            def crypto():
                crypto, mkt_quote = account.get_position.crypto()
                price = mkt_quote.mark_price.astype(float)
                prior_price = mkt_quote.open_price.values.astype(float)
                cost = [float(cost_bases[0]['direct_cost_basis']) for cost_bases in crypto.cost_bases]
                quantity = crypto.quantity.astype(float)
                result = {
                    'symbol':crypto.symbol,
                    'price':price,
                    'pct_change':(price / prior_price - 1) * 100,
                    'quantity':quantity,
                    'pos_$':price * quantity,
                    'pos_%':((price* quantity) / portfolio_value) * 100,
                    'r_$':(price * quantity) - cost,                        # adjust crypto price by fractional shares
                    'r_%':((price * quantity) / cost - 1) * 100,            # adjust crypto price by fractional shares
                    'cost': cost,
                    'inst':'crypto',                  
                }
                result = pd.DataFrame(result).sort_values(by='symbol')
                result = result.dropna(subset=['r_%'])          
                return result

            # Combine tables of equity, options, and crypto
            result = []
            try:    result.append(equity())
            except: pass
            try:    result.append(options())
            except: pass
            try:    result.append(crypto())
            except: pass  
            result = pd.concat(result).reset_index(drop=True)
            return result    
#account.get_position.my_holdings().round(2)
#account.get_position.buying_power()


#%% Market transactions
class orders:
    ''' Routine processes for handling orders/transactions
        + Subdivided into: Equity, Options, Crypto
        + Each asset class contains pre-defined processes for interacting
          with Robinhood
    '''

    #== EQUITIES
    class equity:
        #!! Need email function to send back order placed -- for slippage
        # ---- this is not a limit order
        def place_order(symbol, quantity, side, **kwargs):
            ''' Generic formula to buy/sell equities
                Optional arguments:
                -------------------
                order_type(str):    ‘market’ or ‘limit’
                trigger(str):       ‘immediate’ or ‘stop’ 
                limitPrice(float):  The price to trigger the market order.
                stopPrice(float):   The price to trigger the limit or market order.
                timeInForce(str):   ‘gtc’ = good until cancelled
                                    ‘gfd’ = good for the day
                                    ‘ioc’ = immediate or cancel
                                    ‘opg’ execute at opening.
            '''
            order = r.orders.order(
                symbol=symbol,
                quantity=quantity,
                orderType=kwargs.get('order_type', 'market'),   # market | limit
                trigger=kwargs.get('trigger', 'immediate'),     #??? immediate | stop
                side=side,                                      # buy | sell
                limitPrice=kwargs.get('limitPrice', None),
                stopPrice=kwargs.get('stopPrice',None),
                timeInForce=kwargs.get('timeInForce','gtc'),  #gtc:good-till-cancel | gfd:good-for-day | etc. see docs
            )
            return order

        # Place limit order
        def place_limit_order(symbol, quantity, limitPrice, side, **kwargs):

            if side.lower() == 'buy':
                r.orders.order_buy_limit(
                    symbol=symbol,
                    quantity=quantity,
                    limitPrice=limitPrice,
                    timeInForce=kwargs.get('timeInForce','gtc'),
                )
            if side.lower() == 'sell':
                r.orders.order_sell_limit(
                    symbol=symbol,
                    quantity=quantity,
                    limitPrice=limitPrice,
                    timeInForce=kwargs.get('timeInForce','gtc'),
                )
        
        # Open equity orders
        def open_orders():
            'Returns raw return of all outstanding stock order'
            open_orders = r.orders.get_all_open_stock_orders()    
            open_orders = pd.DataFrame(open_orders)
            symbols = [
                r.stocks.get_instrument_by_url(order)['symbol'] for order in open_orders.instrument
            ]
            open_orders.insert(0,'symbol',symbols)
            return open_orders

        # Cancel all equities order
        def cancel_all_orders():
            'Cancel all outstanding stock order'
            r.orders.cancel_all_stock_orders()
            print('{} -- All stock orders canceled'.format(now()))

        # Cancel by order id
        def cancel_order(order_id):
            r.orders.cancel_stock_order(order_id)
            #print('{now} -- Stock order {order_id} canceled'.format(now=now(), order_id=order_id))

    #== OPTIONS
    #!! RH not great for options -- best not to use RH for options
    class options:

        # Retrieve table of tradable options        
        def list_options(symbol, type='both', market_data=False, **kwargs):
            'Returns df of tradable options'
            'Dont use RH for options data, way too slow. RH does not run each page in parallel'
            
            # Tradable options by symbol
            tradable_option = r.options.find_tradable_options_for_stock(
                symbol=symbol,
                optionType=type       # 'call' | 'put'
            )
            tradable_option = pd.DataFrame(tradable_option)

            # Market data of options
            mkt_quote = []
            if market_data == True:
                for id in tradable_option.id:
                    option_data = r.options.get_option_market_data_by_id(id)    # market data of option
                    mkt_quote.append({
                        'mark':option_data['mark_price'],
                        'volume':option_data['volume'],
                        'open_interest':option_data['open_interest'],
                        'IV':option_data['implied_volatility'],
                        'delta':option_data['delta'],
                        'gamma':option_data['gamma'],
                        'theta':option_data['theta'],
                        'vega':option_data['vega'],
                        'rho':option_data['rho'],
                    })
                #mkt_quote = {key:float(value) for key, value in mkt_quote.items()}
                mkt_quote = pd.DataFrame(mkt_quote)
            else: mkt_quote = None

            # Return results
            return tradable_option, mkt_quote

        # Place order
        # !! WIP 
        def place_order(symbol, quantity, side):
            '''
                positionEffect (str) – Either ‘open’ for a buy to open effect or ‘close’ for a buy to close effect.
                creditOrDebit (str) – Either ‘debit’ or ‘credit’.
                price (float) – The limit price to trigger a buy of the option.
                symbol (str) – The stock ticker of the stock to trade.
                quantity (int) – The number of options to buy.
                expirationDate (str) – The expiration date of the option in ‘YYYY-MM-DD’ format.
                strike (float) – The strike price of the option.
                optionType (str) – This should be ‘call’ or ‘put’
                timeInForce (Optional[str]) – Changes how long the order will be in effect for. ‘gtc’ = good until cancelled. ‘gfd’ = good for the day. ‘ioc’ = immediate or cancel. ‘opg’ execute at opening.
            '''
            '''
            if side == 'buy':
                r.orders.order_buy_option_limit(
                    positionEffect=,    # open | close
                    creditOrDebit=,     # credit | debit
                    price=,             # hi-lo fill
                    symbol=,
                    quantity=quantity,
                    expirationDate=,
                    strike=,
                    optionType=,
                    timeInForce=,
                )
            if side == 'sell'
                r.orders.order_sell_option_limit(
                    positionEffect=,    # open | close
                    creditOrDebit=,     # credit | debit
                    price=,             # hi-lo fill
                    symbol=,
                    quantity=quantity,
                    expirationDate=,
                    strike=,
                    optionType=,
                    timeInForce=,
                )
            '''

        # Open options orders
        # !! WIP
        def open_orders():
            open_orders = r.options.get_open_option_positions()
            
        # Cancel all options orders
        def cancel_all_orders():
            'check if this should be threaded'
            r.orders.cancel_all_option_orders()


    #== CRYPTO
    #!! RH not great for crypto -- user other exchanges/brokers for crypto
    class crypto:
        ''' Crpto mkt functions:
            r.crypto.get_crypto_quote(symbol='BTG')
            r.crypto.get_crypto_info('BTC')
        '''

        # WIP!! -- Place an order
        def place_order(symbol, by, by_value, side):
            ''' by(str): 'amount', 'quantity', 'pct'
            '''
            crypto_info = r.crypto.get_crypto_quote(symbol=symbol)       # get market quotes
            crypto_price = float(crypto_info['mark_price'])
            
            if by=='amount':
                frac_quantity = by_value / crypto_price     # fractional quantity
                r.orders.order_buy_crypto_limit(
                    symbol=symbol,
                    quantity=frac_quantity,
                )
            
            if by=='pct':
                pass

            if by=='price':
                r.orders.order_buy_crypto_by_price(
                    symbol='BCH',
                    amountInDollars=0.1,
                    priceType='mark_price',     # 'ask_price' | 'bid_price' | 'mark_price'
                )

            '''
                if side=='buy':
                    r.orders.order_buy_crypto_by_price(
                        symbol='',
                        amountInDollars=,
                        priceType=,
                    )

                if side=='sell':
                    r.orders.order_sell_crypto_by_price(
                    )
            '''
            '''
            r.oders.order_buy_crypto_by_price(symbol)
            '''
        
        # WIP!! -- Open Crypto orders
        def open_orders():
            open_orders = r.orders.get_all_open_crypto_orders()
            open_orders = pd.DataFrame(open_orders)
            return open_orders

        # Cancel all outstanding crypto order
        def cancel_all_orders():
            r.orders.cancel_all_crypto_orders()            
            print('{} -- All stock orders canceled'.format(now()))

    # Cancel all orders
    def cancel_all_orders():
        'Clear out order book'
        orders.equity.cancel_all_orders()
        orders.options.cancel_all_orders()
        orders.crypto.cancel_all_orders()
        
#orders.stock.cancel_all_orders()
#orders.crypto.place_order(symbol='BTC', by='amount', by_value=0.1, side='buy')
#orders.crypto.cancel_all_orders()
#orders.equity.place_limit_order(symbol='jdst', quantity=1, limitPrice=1, side='buy')