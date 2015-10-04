import random
import uuid

from resources.models.Artist import Artist
from resources.logger import Logger
from searchEngines.imageSearcher import ImageSearcher
from searchEngines.musicBrainz import MusicBrainz
from searchEngines.iTunes import iTunes
from searchEngines.lastFM import LastFM
from searchEngines.spotify import Spotify


class ArtistSearcher(object):

    dbSession = None

    def __init__(self, dbSession, referer=None):
        self.dbSession = dbSession
        self.referer = referer
        if not self.referer or self.referer.startswith("http://localhost"):
            self.referer = "http://github.com/sphildreth/roadie"
        self.logger = Logger()


    def __getArtistFromDB(self,name):
        return self.dbSession.query(Artist).filter(Artist.name == name).first()

    def __saveArtistToDB(self, artist):
        self.dbSession.add(artist)
        self.dbSession.commit()


    def searchForArtist(self, name):
        artist = self.__getArtistFromDB(name)
        if not artist:
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
                #    allMusicSearcher = AllMusicGuide(self.referer)
                #     if allMusicSearcher.IsActive:
                #         artist = artist.mergeWithArtist(allMusicSearcher.lookupArtist(name))
            if artist:
                # Fetch images with only urls
                if artist.images:
                    imageSearcher = ImageSearcher()
                    for image in artist.images:
                        if not image.image and image.url:
                            image.image = imageSearcher.getImageBytesForUrl(image.url)
                self.logger.debug("Saving Artist Info [" + artist.info() + "]")
                if artist.releases:
                    for release in artist.releases:
                        release.roadieId = str(uuid.uuid4())
                        if release.media:
                            for media in release.media:
                                media.roadieId = str(uuid.uuid4())
                                if media.tracks:
                                    for track in media.tracks:
                                        track.roadieId = str(uuid.uuid4())
                self.__saveArtistToDB(artist)
        foundArtistName = None
        if artist:
            foundArtistName = artist.name
        self.logger.debug("artistSearcher :: searchForArtist Name [" + name + "] Found [" + str(foundArtistName) + "]")
        return artist

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
