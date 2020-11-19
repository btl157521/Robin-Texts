''' Custom application functions and processes
    + These are the instructions for custom text message commands
'''
#%% Import Packages
import os, sys
import config as config              # account information
import RH.Reports.RH_functions as rh    # custom RH functions

import datetime as dt
import pandas as pd
import robin_stocks as r

import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment

TEMPLATE_PATH = os.path.join(os.getcwd(),'RH','Reports','report_templates')   # path to html templates

#%% Runtime timer
def function_timer(function, args=None):
    'Executes given function and returns runtime'
    start_timer = dt.datetime.now()
    for f in function: 
        if args==None: 
            f()             # execute no args
        else: 
            f(args)         # execute w/ args
    end_timer = dt.datetime.now() - start_timer
    return end_timer

#%% Now time
def now():
    'Return now time, cleanly formatted'
    datetime = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return datetime


# Email server processes
class email_server:
    ''' Routine processes for interacting with email server
    '''
    
    # Initialize login information
    def __init__(self, user_info=config.user_info):
        'Account info should be a dictionary'
        self.email_user = user_info['email']['username']
        self.email_password = user_info['email']['password']
        self.email_bot = user_info['email']['username']            # ?Needed? seems duplicate

    # Connect to gmail
    def connect_gmail(self):
        email = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        email.login(user=self.email_user, password=self.email_password)
        return email

    # Connect to email server
    def connect_smtp(self):
        server = smtplib.SMTP(host='smtp.gmail.com', port=587)
        server.starttls()
        server.login(user=self.email_user, password=self.email_password)    # login and standby for template to send
        return server
    
    # Stop all connections
    # !! Is this necessary?
    def disconnect_all(self, client, server):
        email_server.quit()
        email_client.logout()

    # Fetch unread email from inbox
    def get_unread_mail(self, e_client, inbox_name):
        'Selects given inbox of given email client and returns unread emails'
        e_client.select(inbox_name)                                 # select inbox
        unread_mail = e_client.search(None,'Unseen')[1]             # unread emails
        mail_ids = unread_mail[0].split()                           # email ids
        result = []
        for id in mail_ids:
            mail_item = e_client.fetch(id,'(BODY.PEEK[])')                        # get msg from email
            msg = email.message_from_string(mail_item[1][0][1].decode('utf-8'))   # convert to string
            result.append({
                'msg_id':id,
                'datetime':pd.to_datetime(msg['received'].split('\r\n')[-1].strip()).astimezone(tz='US/Eastern'),
                'from':msg['from'],
                'to':msg['to'],
                'subject':msg['subject'],
                'body':msg.get_payload(),
            })
        return result


# Custom application functions/processes
class app_functions:
    ''' Receives command from Process_routes.py and executes
        pre-defined process. 
    '''

    # Fetch current holdings
    def current_holdings(e_server):
        'Retrieves account info from robinhood and email a custom report of current holdings'
        '!! Cant handle when holdings is empty df'
        '!! Make separate case for when there is no open positions'
        
        # Get account information from RH
        account_profile = r.profiles.load_account_profile()
        portfolio = r.profiles.load_portfolio_profile()
        holdings = rh.account.get_position.my_holdings()                        # all open positions

        # Calculate portfolio aggregates
        positions =         holdings['pos_$'].sum()
        buying_power =      float(account_profile['buying_power'])
        portfolio_value =   positions + buying_power                            # total portfolio $
        daily_change =      (portfolio_value / 
                             float(portfolio['adjusted_portfolio_equity_previous_close']) - 1
                            ) * 100
        cash_pct =          buying_power / portfolio_value                      # total cash %
        pos_pct =           positions / portfolio_value                         # total positions %
        pos_cost =          (holdings['pos_$'].sum() - holdings['r_$'].sum())   # total position cost
        return_dollars =    holdings['r_$'].sum() 
        return_pct =        (holdings['r_$'].sum() / pos_cost) * 100
        aggregates = {
            'daily_change':         daily_change.round(2),
            'total_position_value': positions,
            'total_buying_power':   buying_power,
            'total_portfolio_value':portfolio_value,
            'total_position_cost':  pos_cost,
            'position_pct':         pos_pct*100,
            'cash_pct':             cash_pct*100,
            'return_$':             return_dollars,
            'return_%':             return_pct
        }
        aggregates = {key:'{:,.2f}'.format(value) for key, value in aggregates.items()}

        # Construct email
        path = os.path.join(TEMPLATE_PATH, 'current_holdings.html')
        TEMPLATE = open(path,'r').read() 
        msg = MIMEText(
            Environment().from_string(TEMPLATE).render(
                h=holdings.round(2),
                agg=aggregates,
                dt=dt.datetime.now().strftime('%Y-%m-%d  %H:%M:%S')[:-4],
            ), 
            'html'
        )

        # Send email
        msg['Subject'] = '[Current]'
        msg['From'] = email_server().email_bot
        msg['To'] = email_server().email_bot
        e_server.sendmail(
            from_addr=email_server().email_bot, 
            to_addrs=email_server().email_bot, 
            msg=msg.as_string()
        )


    # Cancel all open orders
    def cancel_orders():
        'cancels all orders'
        rh.orders.cancel_all_orders()


    # Limit buy/sell
    def equity_limit_order(COMMAND):
        'Equity limit order'

        # Parse order parameters from COMMAND
        COMMAND = COMMAND.as_string().strip().split('\n')      
        order_type = COMMAND[0].split(' ')
        order_detail = COMMAND[1].split(' ')
        order_params = {
            'type':order_type[0].upper(),
            'side':order_type[1].upper(),
            'instrument':order_type[2].upper(),
            'quantity':float(order_detail[0]),
            'symbol':order_detail[1],
        }

        # Get market quote of stock
        mkt_quote = r.stocks.get_stock_quote_by_symbol(order_params['symbol'])
        mkt_price = float(mkt_quote['last_extended_hours_trade_price'])
        mkt_dt = mkt_quote['updated_at']

        # Adjust mkt price by MAX/MIN pct and place limit order
        if   'MAX' in COMMAND: adj_di = 1        
        elif 'MIN' in COMMAND: adj_di = -1
        else:                  adj_di = 0
        price_adjuster = order_detail[-2:]
        adj_pct = float(price_adjuster[1]) / 100    #!!! PCT ADJUSTER (0.3 == 0.3%)
        price_adjuster = (1 + (adj_di * adj_pct))   # adjust mkt price by limit pct
        LIMIT_PRICE = mkt_price * price_adjuster    # calculate limit price

        # What to do when MAX/MIN not provided; instead limitPrice is provided
        # !! WIP
        if adj_di == 0:
            'LIMIT_PRICE = order_details[-1]'

        # Send order to RH
        rh.orders.equity.place_limit_order(
            symbol=order_params['symbol'].lower(),
            quantity=order_params['quantity'],
            side=order_params['side'].lower(),
            limitPrice=LIMIT_PRICE,
        )


    # Fetch all open orders (WIP)
    def open_orders():
        TRIGGER = ['ORDERS', 'OPEN ORDERS']

# %%
