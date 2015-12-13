import json
from io import StringIO
from urllib import request, parse
from resources.common import *
from searchEngines.searchEngineBase import SearchEngineBase
from searchEngines.imageSearcher import ImageSearcher
from searchEngines.models.Artist import Artist
from searchEngines.models.Genre import Genre
from searchEngines.models.Image import Image
from searchEngines.models.Release import Release


class iTunes(SearchEngineBase):
    IsActive = True

    imageSearcher = None

    cache = dict()

    def __init__(self, referer=None):
        self.imageSearcher = ImageSearcher(referer)
        SearchEngineBase.__init__(self, referer)

    def lookupArtist(self, name):
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

    def searchForRelease(self, artist, title):
        if not artist or not artist.name or not title:
            return None
        if not artist.iTunesId:
            artist = self.lookupArtist(artist.name)
            if not artist or not artist.iTunesId:
                return None
        try:
            if artist.roadieId in self.cache and not title:
                self.logger.debug(
                    "Found Artist: roadieId [" + artist.roadieId + "] name [" + artist.name + "] in iTunes Cache.")
                return self.cache[artist.roadieId]
            url = "https://itunes.apple.com/lookup?id=" + str(artist.iTunesId) + "&entity=album"
            rq = request.Request(url=url)
            rq.add_header('Referer', self.referer)
            releases = []
            if artist.roadieId not in self.cache:
                self.logger.debug("Performing iTunes Lookup For Album(s)")
                with request.urlopen(rq) as f:
                    try:
                        s = StringIO((f.read().decode('utf-8')))
                        o = json.load(s)
                        for r in o['results']:
                            try:
                                if 'collectionType' in r and isEqual(r["collectionType"], "Album"):
                                    a = Release(title=r['collectionName'], releaseDate=r['releaseDate'])
                                    a.trackCount = r['trackCount']
                                    a.iTunesId = r['collectionId']
                                    if 'primaryGenreName' in r and r['primaryGenreName']:
                                        a.genres.append(Genre(name=r['primaryGenreName']))
                                    if 'artistViewUrl' in r and r['artistViewUrl']:
                                        a.urls.append(r['artistViewUrl'])
                                    if 'collectionViewUrl' in r and r['collectionViewUrl']:
                                        a.urls.append(r['collectionViewUrl'])
                                    if not a.alternateNames:
                                        a.alternateNames = []
                                    cleanedTitle = createCleanedName(a.title)
                                    if cleanedTitle not in a.alternateNames and cleanedTitle != a.title:
                                        a.alternateNames.append(cleanedTitle)
                                    images = self.imageSearcher.itunesSearchArtistReleaseImages(artist.name, a.title)
                                    if images:
                                        a.images = []
                                        for i in images:
                                            a.images.append(Image(i.url))
                                            releases.append(a)
                            except:
                                self.logger.exception("iTunes: Error In SearchForRelease")
                                pass
                    except:
                        pass
                self.cache[artist.roadieId] = sorted(releases, key=lambda x: (x.weight(), x.releaseDate, x.title))
                if title:
                    foundRelease = None
                    for release in self.cache[artist.roadieId]:
                        if isEqual(release.title, title):
                            foundRelease = release
                            break
                    if foundRelease:
                        releases = [foundRelease]
                        return releases
                    else:
                        return None
            return self.cache[artist.roadieId]
        except:
            self.logger.exception("iTunes: Error In SearchForRelease")
            pass
        return None

# s = iTunes()
# artist = s.lookupArtist("Iron Maiden")
# release = s.searchForRelease(artist, "A Matter Of Life And Death")
# uprint(release.info())
