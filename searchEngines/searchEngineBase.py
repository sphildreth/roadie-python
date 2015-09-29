from abc import ABCMeta, abstractmethod
from resources.logger import Logger

class SearchEngineBase:

    __metaclass__ = ABCMeta

    def __init__(self, referer):
        self.referer = referer
        if not self.referer or self.referer.startswith("http://localhost"):
            self.referer = "http://github.com/sphildreth/roadie"
        self.logger = Logger()


    @abstractmethod
    def lookupArtist(self, name): pass


    @abstractmethod
    def searchForRelease(self, artistSearchResult, title): pass
