""" Log
"""
#%% Import packages
import os
import sys
import logging

log_folder = os.path.join(os.getcwd(),'RH','Log')

class log:

    def __init__(self, **kwargs):
        self.params = {
            'level':kwargs.get('level','DEBUG'),
        }
        self.log = logging.getLogger('APP')     # LOGGER
        self.log.setLevel(self.params['level']) # set logging level
        self.attach_handlers()                  # attach log handlers

    def attach_handlers(self):
        "Attach logging objects to logger"
        # Create handlers
        self.stdout = logging.StreamHandler()
        self.log_file = logging.FileHandler(os.path.join(log_folder, 'log_INFO.txt'))

        # Format handler
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(levelname)s - Line %(lineno)d - [%(filename)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )
        self.stdout.setFormatter(formatter)
        self.log_file.setFormatter(formatter)

        # Attach handler
        self.log.addHandler(self.stdout)
        self.log.addHandler(self.log_file)

    def close(self):
        "Close logging objects"
        self.stdout.close()
        self.log_file.close()
        self.log.removeHandler(self.stdout)
        self.log.removeHandler(self.log_file)
