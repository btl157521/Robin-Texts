''' Launch Application
'''
#%% Import packages
import datetime as dt
import config as config              # configurables file
import RH.Reports.RH_functions as rh    # robinhood processes
import RH.Reports.APP_functions as app  # application processes
import RH.Process_routes as routes      # routes
import RH.Log.logger as logger

#%% Start log
LOGGER = logger.log()              
LOG = LOGGER.log                    
LOG.info('Log initialized')

#%% APPLICATION (Launch APP)
try:
    # Initialize connection to RH and email server
    start_conn_timer = dt.datetime.now()                    # start connection timer
    rh.app().connect_robinhood()                            # login to RH
    e_client = app.email_server().connect_gmail()                 
    e_server = app.email_server().connect_smtp()           
    LOG.info('All connections initialized')

    # Start forever loop
    while True:

        # Update process running msg so we know its running
        print('{now} -- [{file_name}] Process running'.format(
            now=rh.now(), 
            file_name=__file__.split('\\')[-1]), 
            end='\r'
        )      
        
        # Every 15-minutes, reset conections
        #!! To clean this up, use YIELD instead of RETURN to pass values from inside while loop
        timer = 60 * 15                                 # 60-second * 15-minutes
        time_buffer = 0.5
        conn_timer = (dt.datetime.now() - start_conn_timer)
        if conn_timer > dt.timedelta(seconds=timer + time_buffer):
            start_conn_timer = dt.datetime.now()                    # reset timer
            rh.connections().connect_robinhood()                    # login to RH
            e_client = app.email_server().connect_gmail()                 
            e_server = app.email_server().connect_smtp() 
            LOG.info('All connections reset')
        
        # Read inbox for unread + process
        UNREAD_MSG = app.email_server().get_unread_mail(e_client=e_client, inbox_name='Inbox')
        routes.PROCESS_UNREAD_MSG(
            unread_email=UNREAD_MSG, 
            email_client=e_client,
            email_server=e_server,
        )
        
except KeyboardInterrupt:
    LOG.exception('EXIT -- Keyboard interruption')

except:
    LOG.exception('EXIT -- !!! FAILURE !!!')


# Close log
LOG.info('Closing log')
LOGGER.close()