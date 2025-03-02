"""
logger.py – Implements a simple Logger class.
Logs download activities, errors, and status updates to both a file and the console.
"""

import logging

class Logger:
    def __init__(self, log_file="idm_log.txt"):
        logging.basicConfig(filename=log_file, level=logging.INFO,
                            format="%(asctime)s - %(levelname)s - %(message)s")
        self.log_file = log_file
        
    def log(self, message):
        logging.info(message)
        print(message)  # Also print to the console
