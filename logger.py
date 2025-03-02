"""
logger.py – Logs messages to a file and prints to console.
"""

import logging
import sys

class Logger:
    def __init__(self, log_file="idm_log.txt"):
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
        )
        self.log_file = log_file

    def log(self, message):
        logging.info(message)
        print(message, file=sys.stdout)
