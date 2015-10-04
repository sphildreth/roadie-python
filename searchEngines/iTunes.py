import json
from io import StringIO
from urllib import request, parse

from resources.common import *
from searchEngines.searchEngineBase import SearchEngineBase
from searchEngines.models.Artist import Artist
from searchEngines.models.Release import Release


class iTunes(SearchEngineBase):

    IsActive = True

    def __init__(self, referer=None):
        SearchEngineBase.__init__(self, referer)


    def lookupArtist(self,name):
        try:
            artist = None
            url = "http://itunes.apple.com/search?term=" + parse.quote_plus(name) + "&entity=musicArtist"
            rq = request.Request(url=url)
            rq.add_header('Referer', self.referer)
            self.logger.debug("Performing iTunes Lookup For Artist")
            with request.urlopen(rq) as f:
                try:
                    s = StringIO((f.read().decode('utf-8')))
                    o = json.load(s)
                    for r in o['results']:
                        artist = Artist(name=r['artistName'])
                        if 'artistId' in r:
                            artist.iTunesId = r['artistId']
                        if 'amgArtistId' in r:
                            artist.amgId = r['amgArtistId']
                        if isEqual(artist.name, name):
                            break
                except:
                    self.logger.exception("iTunes: Error In LookupArtist")
                    pass
                    #   if artist:
                    #        print(artist.info())
            return artist
        except:
            self.logger.exception("iTunes: Error In LookupArtist")
            pass
        return None


    def searchForRelease(self,artistSearchResult,title):
        if not artistSearchResult.iTunesId:
            artistSearchResult = self.lookupArtist(artistSearchResult.name)
            if not artistSearchResult.iTunesId:
                raise RuntimeError("Invalid ArtistSearchResult, iTunesId Not Set")
        try:
            url = "https://itunes.apple.com/lookup?id=" + str(artistSearchResult.iTunesId) + "&entity=album"
            rq = request.Request(url=url)
            rq.add_header('Referer', self.referer)
            albumsSearchResult = []
            self.logger.debug("Performing iTunes Lookup For Album(s)")
            with request.urlopen(rq) as f:
                try:
                    s = StringIO((f.read().decode('utf-8')))
                    o = json.load(s)
                    for r in o['results']:
                        try:
                            if 'collectionType' in r and isEqual(r["collectionType"], "Album"):
                                a = Release(title=r['collectionName'], releaseDate=r['releaseDate'],
                                            trackCount=r['trackCount'], coverUrl=r['artworkUrl100'])
                                a.iTunesId = r['collectionId']
                                albumsSearchResult.append(a)
                        except:
                            pass
                except:
                    pass
            albumsSearchResult = sorted(albumsSearchResult, key=lambda x: x.releaseDate)
            return albumsSearchResult[0]
        except:
            self.logger.exception("iTunes: Error In SearchForRelease")
            pass
        return None