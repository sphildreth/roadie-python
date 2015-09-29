import requests
import time
import hashlib
from urllib.parse import *
import json
from io import StringIO
from urllib import request, parse
from searchEngines.searchResult import *
from searchEngines.searchEngineBase import SearchEngineBase

class AllMusicGuide(object):

    IsActive = False

    api_url = 'http://api.rovicorp.com/data/v2'

    API_KEY = '5um457xsnur2a6hp43vuarrs'
    API_SECRET = 'SuGNstff77'

    def __init__(self, referer=None):
        SearchEngineBase.__init__(self, referer)

    def _sig(self):
        timestamp = int(time.time())
        m = hashlib.md5()
        m.update(self.API_KEY.encode('utf-8'))
        m.update(self.API_SECRET.encode('utf-8'))
        m.update(str(timestamp).encode('utf-8'))
        return m.hexdigest()

    def lookupArtist(self,name):
        #http://api.rovicorp.com/search/v2/music/search?apikey=apikey&sig=sig&query=eric+clapton&entitytype=artist&size=1&include=artist:memberof

        #http://api.rovicorp.com/search/v2/music/search?apikey=apikey&sig=sig&query=eric+clapton&endpoint=music&entitytype=artist&include=all
     #   try:
        url = "http://api.rovicorp.com/search/v2/music/search?apikey=" + self.API_KEY + "&sig=" + str(self._sig()) + "&query=" + parse.quote_plus(name) +"&entitytype=music&entitytype=artist&include=all"
        rq = request.Request(url=url)
        rq.add_header('Referer', self.referer)
        albumsSearchResult = []
        print(url);
        self.logger.debug("artistSearcher :: Performing All Music Guide Lookup For Album(s)")
        with request.urlopen(rq) as f:
      #      try:
            s = StringIO((f.read().decode('utf-8')))
            o = json.load(s)
            print(o)
            #for r in o['results']:
                # try:
                #     if 'collectionType' in r and r["collectionType"] == "Album":
                #         a = ArtistReleaseSearchResult(r['collectionName'], r['releaseDate'], r['trackCount'], r['artworkUrl100'])
                #         a.iTunesId = r['collectionId']
                #         albumsSearchResult.append(a)
                # except:
                #     pass
          #  except:
        #        pass
        albumsSearchResult = sorted(albumsSearchResult, key=lambda x: x.releaseDate)
        return albumsSearchResult
    #    except:
    #        self.logger.exception("iTunes: Error In SearchForRelease")
    #        pass
    #    pass


    def searchForRelease(self,artistSearchResult,title):
        #http://api.rovicorp.com/data/v1.1/release/info?apikey=apikey&sig=sig&releaseid=MR0002392414
     #   try:
        url = "http://api.rovicorp.com/data/v1.1/release/info?apikey=apikey&sig=sig&releaseid=MR0002392414"
        rq = request.Request(url=url)
        rq.add_header('Referer', self.referer)
        albumsSearchResult = []
        self.logger.debug("artistSearcher :: Performing All Music Guide Lookup For Album(s)")
        with request.urlopen(rq) as f:
      #      try:
            s = StringIO((f.read().decode('utf-8')))
            o = json.load(s)
            print(o)
            #for r in o['results']:
                # try:
                #     if 'collectionType' in r and r["collectionType"] == "Album":
                #         a = ArtistReleaseSearchResult(r['collectionName'], r['releaseDate'], r['trackCount'], r['artworkUrl100'])
                #         a.iTunesId = r['collectionId']
                #         albumsSearchResult.append(a)
                # except:
                #     pass
          #  except:
        #        pass
        albumsSearchResult = sorted(albumsSearchResult, key=lambda x: x.releaseDate)
        return albumsSearchResult
    #    except:
    #        self.logger.exception("iTunes: Error In SearchForRelease")
    #        pass
    #    pass


# Had to wait as AMG API key returns "<h1>403 Developer Inactive</h1>"

# a = AllMusicGuide()
# a.lookupArtist('Men At Work')
# print(a)