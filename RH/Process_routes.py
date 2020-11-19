''' Application process routes
    + This is effectively a map of how a command from the user will be translated 
      into appropriate application process.
    + Listen to defined email inbox for commands from user
        - commands are defined in config.py
        - When command is triggered, execute pre-defined process
'''
#%%
import config as config              # application configurables file
import RH.Reports.RH_functions as rh    # custom rh functions
import RH.Reports.APP_functions as app  # custom functions
import datetime as dt
import email

#%% Routes processor
#   Map of how texted instructions will be processed
def PROCESS_UNREAD_MSG(unread_email, email_client, email_server):
    ''' Main process
        + Searches email for unread messages
        + If messages are from phone number defined in 'config.py', process
          message into command for Robinhood
        + Command trigger words are defined by user in 'config.py'
        + Map of how a command will match custom reporting function

        For each unread email, check if email was sent from 'phone_address'.
        If the email is from address, search the text found in the body for
        matches with commands from config.py. If a match is found, mark the
        email as 'READ' and pass the appropraite application process to
        function_timer() to execute. Print total runtime when process is completed.
    '''
    # Read unread email
    for mail in unread_email:
        
        # Parse unread mail
        msg = {
            'id':       mail['msg_id'],
            'from':     mail['from'],
            'date':     mail['datetime'],
            'subject':  mail['subject'],
            'body':     email.message_from_string(mail['body'])
        }

        # Verify sender of email to match phone number (defined in config.py file)
        # Proceed if matched, else ignore
        if msg['from'] == config.user_info['phone_address']:
            ''' !!! Text message construct:
                + MARKET COMMANDS FROM PHONE SHOULD BE CONSTRUCTED AS:
                    [Transaction type] [Side] [Instrument]
                    [Quantity] [Symbol] [Price/Pct]
                + OTHER COMMANDS (case-insensitive):
                    Current holdings
                    Cancell all / Cancel
            '''

            # Fetch user's command from email
            COMMAND = msg['body'].as_string().upper()     

            #=== CURRENT HOLDINGS
            COMMAND_TRIGGERS = config.commands['current_holdings']
            if any(trigger in COMMAND for trigger in COMMAND_TRIGGERS):
                email_client.store(msg['id'], '+FLAGS', '\Seen')    # mark email as read
                # Run process in function_timer()
                runtime = app.function_timer(                           
                    function=[app.app_functions.current_holdings],
                    args=email_server
                )
                # Print runtime message
                print('{now} -- [CURRENT HOLDINGS] Executed command [Runtime: {runtime}]'.format(
                    now=app.now(), 
                    runtime=runtime
                )) 

            #=== CANCEL ALL ORDERS
            COMMAND_TRIGGERS = config.commands['cancel_orders']
            if any(trigger in COMMAND for trigger in COMMAND_TRIGGERS):
                email_client.store(msg['id'], '+FLAGS', '\Seen')    # mark email as read
                # Run process in function_timer()
                runtime = app.function_timer(
                    function=[app.app_functions.cancel_orders],
                    args=None
                )
                # Print runtime message
                print('{now} -- [CANCEL ALL ORDERS] Executed command [Runtime: {runtime}]'.format(
                    now=app.now(), 
                    runtime=runtime
                ))

            #=== LIMIT BUY/SELL ORDER
            COMMAND_TRIGGERS = config.commands['limit_order']
            if any(trigger in COMMAND for trigger in COMMAND_TRIGGERS):
                email_client.store(msg['id'], '+FLAGS', '\Seen')   # mark email as read

                #--- Equity
                COMMAND_TRIGGERS = config.commands['instruments']['equities']
                if any(trigger in COMMAND for trigger in COMMAND_TRIGGERS):
                    # Run process in function_timer()
                    runtime = app.function_timer(
                        function=[app.app_functions.equity_limit_order],
                        args=msg['body']
                    )
                    # Print runtime message
                    print('{now} -- [STOCK ORDER] Executed command [Runtime: {runtime}]'.format(
                        now=app.now(), 
                        runtime=runtime
                    ))

                #--- Options
                COMMAND_TRIGGERS = config.commands['instruments']['options']
                if any(trigger in COMMAND for trigger in COMMAND_TRIGGERS):
                    # WIP
                    pass

                #--- Crypto
                COMMAND_TRIGGERS = config.commands['instruments']['crypto']
                if any(trigger in COMMAND for trigger in COMMAND_TRIGGERS):
                    # WIP
                    pass          
            
            #=== ALL OPEN ORDERS
            COMMAND_TRIGGERS = config.commands['open_orders']
            if any(trigger in COMMAND for trigger in COMMAND_TRIGGERS):
                # WIP
                pass    

            #=== CUSTOM COMMAND
