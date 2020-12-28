""" APP
    Program execution file.
"""
#%% Import packages
import config as config                 # configurables file
import os, sys
import datetime as dt
import asyncio
import smtplib
import RH.Reports.RH_functions as rh    # robinhood processes
import RH.Reports.APP_functions as app  # application processes
import RH.Process_routes as routes      # routes
import RH.Log.logger as logger
 

async def rh_login():
    """ Login to Robinhood every 15-minutes.
    """
    timer = 60 * 15     # 15 minutes
    while True:
        await asyncio.sleep(timer)
        rh.app().connect_robinhood()        # connect to rH

async def email_connect(e_client, e_server):
    """ Refreshes email client and server objects.
    """
    timer = 60 * 15     # 15 minutes
    while True:
        await asyncio.sleep(timer)
        e_client = app.email_server().connect_gmail()
        e_server = app.email_server().connect_smtp()

async def process_mail(e_client, e_server):
    """ Processes email. 
        Routes are defined in "Process_routes.py"
    """
    while True:
        await asyncio.sleep(0.1)

        # Try to read message. If error, reconnect and try again.
        try:
            UNREAD_MSG = app.email_server().get_unread_mail(e_client=e_client, inbox_name='Inbox')
        except Exception as e:
            # Refresh connection and read msg again
            e_client = app.email_server().connect_gmail()
            e_server = app.email_server().connect_smtp()
            UNREAD_MSG = app.email_server().get_unread_mail(e_client=e_client, inbox_name='Inbox')

        # Process message
        routes.PROCESS_UNREAD_MSG(
            unread_email=UNREAD_MSG, 
            email_client=e_client,
            email_server=e_server,
        )


if __name__=='__main__':
    # Launch application
    sys.stdout.write('Starting Robin-Texts')

    # Log
    LOGGER = logger.log()               # initialize class
    LOG = LOGGER.log                    # log 
    LOG.info('Log initialized')

    # Async processes
    try:
        # Initial load
        rh.app().connect_robinhood()
        e_client = app.email_server().connect_gmail()
        e_server = app.email_server().connect_smtp()

        # Create tasks
        APP = asyncio.get_event_loop()                      # scheduler
        APP.create_task(rh_login())                         # refresh RH connection
        APP.create_task(email_connect(e_client, e_server))  # refresh email connections
        APP.create_task(process_mail(e_client, e_server))

        # Launch tasks
        APP.run_forever()

    except KeyboardInterrupt:
        LOG.exception('EXIT -- Keyboard interruption')

    except Exception as error:
        LOG.exception('ERROR --{}'.format(error))

    # Close application
    APP.close()     # close out
    LOG.info('Closing log')
    LOGGER.close()
