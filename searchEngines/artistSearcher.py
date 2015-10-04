import random
import uuid

from resources.models.Artist import Artist as dbArtist
from resources.models.Label import Label as dbLabel
from resources.logger import Logger
from searchEngines.imageSearcher import ImageSearcher
from searchEngines.musicBrainz import MusicBrainz
from searchEngines.iTunes import iTunes
from searchEngines.lastFM import LastFM
from searchEngines.spotify import Spotify
from searchEngines.allMusic import AllMusicGuide
from searchEngines.models.Artist import Artist


class ArtistSearcher(object):

    dbSession = None

    cache = dict()

    def __init__(self, dbSession, referer=None):
        self.dbSession = dbSession
        self.referer = referer
        if not self.referer or self.referer.startswith("http://localhost"):
            self.referer = "http://github.com/sphildreth/roadie"
        self.logger = Logger()


    def __getArtistFromDB(self,name):
        return self.dbSession.query(dbArtist).filter(dbArtist.name == name).first()

    def __getLabelFromDB(self, name):
        return self.dbSession.query(dbLabel).filter(dbLabel.name == name).first()

    def searchForArtist(self, name):
        if name in self.cache:
            return self.cache[name]
        result = self.__getArtistFromDB(name)
        if not result:
            artist = Artist(name=name)
            artist.random = random.randint(1, 9999999)
            artist.roadieId = str(uuid.uuid4())
            iTunesSearcher = iTunes(self.referer)
            if iTunesSearcher.IsActive:
                artist = artist.mergeWithArtist(iTunesSearcher.lookupArtist(name))
            mbSearcher = MusicBrainz(self.referer)
            if mbSearcher.IsActive:
                artist = artist.mergeWithArtist(mbSearcher.lookupArtist(name))
            lastFMSearcher = LastFM(self.referer)
            if lastFMSearcher.IsActive:
                artist = artist.mergeWithArtist(lastFMSearcher.lookupArtist(name))
            spotifySearcher = Spotify(self.referer)
            if spotifySearcher.IsActive:
                artist = artist.mergeWithArtist(spotifySearcher.lookupArtist(name))
            allMusicSearcher = AllMusicGuide(self.referer)
            if allMusicSearcher.IsActive:
                artist = artist.mergeWithArtist(allMusicSearcher.lookupArtist(name))
            if artist:
                # Fetch images with only urls
                if artist.images:
                    imageSearcher = ImageSearcher()
                    for image in artist.images:
                        if not image.image and image.url:
                            image.image = imageSearcher.getImageBytesForUrl(image.url)
                self.cache[name] = artist
                self.logger.debug("Saving Artist Info [" + artist.info() + "]")
                #   self.dbSession.expunge(artist)
                # self.dbSession.add(artist)
                #   self.dbSession.commit()
                result = artist
        foundArtistName = None
        if result:
            foundArtistName = result.name
        self.logger.debug("searchForArtist Name [" + name + "] Found [" + str(foundArtistName) + "]")
        return result

    def searchForArtistReleases(self, artist, titleFilter=None):
        # albumsSearchResult = self.__getAlbumsForArtistFromDB(artistSearchResult)
        # if not albumsSearchResult:
        #     albumsSearchResult = self.__iTunesAlbumsForArtist(artistSearchResult, titleFilter)
        #     if albumsSearchResult:
        #         albumsSearchResult = self.__markReleasesFoundInRoadie(artistSearchResult, albumsSearchResult)
        #         self.__saveReleasesForArtistToDB(artistSearchResult, albumsSearchResult)
        # result = albumsSearchResult
        # if titleFilter:
        #     result = []
        #     for a in albumsSearchResult:
        #         if a.title.lower() == titleFilter.lower():
        #             result.append(a)
        #             continue
        # return result
        pass
