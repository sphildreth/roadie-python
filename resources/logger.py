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

    def debug(self,message):
        #message.encode('utf-8')
        self.logger.debug(message)


    def info(self,message):
        self.logger.info(message)

    def warn(self,message):
        self.logger.warn(message)

    def error(self,message):
        self.logger.error(message)

    def exception(self,*message):
        """
        Get last exception and print message to logger including any optional message

        """
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        self.logger.error('{}: EXCEPTION IN ({}, LINE {} "{}"): {}'.format(message, filename, lineno, line.strip(), exc_obj))


    def critical(self,message):
        self.logger.critical(message)

