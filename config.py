''' Application configurables
    + user_info
    + commands
'''

#%% User info
''' Define user information in 'account_info'.
    When the application needs user-unique information,
    it'll refer to this object to get login information
    to email server and Robinhood.
    
    To get value for 'phone_address', send a text message
    to your email and see where it was sent from. This
    application will only accept instructions from the
    address define in 'phone_address'.
'''
user_info = {
    'phone_address':'',             # your phone address -- bot will only read commands from this number
    'email':{
        'server':'',                # 'gmail.com', 'outlook.com'
        'username':'',              # email address of bot
        'password':''
    },
    'robinhood':{
        'username':'',
        'password':''
    },
}

#%% User defined commands
''' Define command words to trigger custom instructions.
    The application will read the emails sent from the user
    and search for defined command words. If the command word
    is detected, the application will run the appropriate process.
''' 
commands = {
    # Get current portfolio holdings
    'current_holdings':[
        'CURRENT',
        'CURRENT HOLDINGS',
    ],
    
    # Cancel all outstanding orders
    'cancel_orders':[
        'CANCEL',
        'CANCEL ALL',
    ],

    # Limit orders
    'limit_order':[
        'LIMIT BUY',
        'LIMIT SELL',
    ],

    # Open orders
    'open_orders':[
        'O',
        'OPEN',
        'OPEN ORDERS',
    ],

    # Instruments -- helps route msg to appropriate function
    'instruments':{
        'equities':[
            'E',
            'EQUITY',
            'S',
            'STOCK'
        ],
        'options':[
            'O',
            'OPTION',
            'OPTIONS'
        ],
        'crypto':[
            'C',
            'CRYPTO'
        ]
    },
}
