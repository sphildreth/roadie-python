import os
import sys
import linecache
import logging
import logging.config
from pymitter import EventEmitter


class Logger(object):
    logger = None

    ee = EventEmitter()

    def __init__(self):
        d = os.path.dirname(os.path.realpath(__file__)).split(os.sep)
        path = os.path.join(os.sep.join(d[:-1]), "logging.conf")
        logging.config.fileConfig(path)
        self.logger = logging.getLogger('simpleExample')

    def debug(self, message):
        self.ee.emit("log", "debug", message)
        self.logger.debug(message)

    def info(self, message):
        self.ee.emit("log", "info", message)
        self.logger.info(message)

    def warn(self, message):
        self.ee.emit("log", "warn", message)
        self.logger.warn(message)

    def error(self, message):
        self.ee.emit("log", "error", message)
        self.logger.error(message)

    def exception(self, *message):
        """
        Get last exception and print message to logger including any optional message

        """
        self.ee.emit("log", "exception", message)
        self.logger.exception(message)

    def critical(self, message):
        self.ee.emit("log", "critical", message)
        self.logger.critical(message)
