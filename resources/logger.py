import os
import sys
import linecache
import logging
import logging.config


class Logger(object):
    logger = None

    def __init__(self):
        d = os.path.dirname(os.path.realpath(__file__)).split(os.sep)
        path = os.path.join(os.sep.join(d[:-1]), "logging.conf")
        logging.config.fileConfig(path)
        self.logger = logging.getLogger('simpleExample')

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warn(self, message):
        self.logger.warn(message)

    def error(self, message):
        self.logger.error(message)

    def exception(self, *message):
        """
        Get last exception and print message to logger including any optional message

        """
        logging.exception(message)

    def critical(self, message):
        self.logger.critical(message)
