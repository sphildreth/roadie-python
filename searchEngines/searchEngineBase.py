import json
import threading
from queue import Queue
from io import StringIO
from urllib import request

from abc import ABCMeta, abstractmethod
from resources.logger import Logger


class ThreadData(object):

    def __init__(self, threadDataType, data):
        self.threadDataType = threadDataType
        self.data = data


class SearchEngineBase:

    __metaclass__ = ABCMeta

    threadCount = 16


    def __init__(self, referer):
        self.referer = referer
        if not self.referer or self.referer.startswith("http://localhost"):
            self.referer = "http://github.com/sphildreth/roadie"
        self.logger = Logger()


    @abstractmethod
    def lookupArtist(self, name): pass


    @abstractmethod
    def searchForRelease(self, artistSearchResult, title): pass
