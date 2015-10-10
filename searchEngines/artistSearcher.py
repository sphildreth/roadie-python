import random
import uuid

from resources.common import *
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

    allMusicSearcher = None

    cache = dict()

    def __init__(self, dbSession, referer=None):
        self.dbSession = dbSession
        self.referer = referer
        if not self.referer or self.referer.startswith("http://localhost"):
            self.referer = "http://github.com/sphildreth/roadie"
        self.logger = Logger()
        self.allMusicSearcher = AllMusicGuide(self.referer)

    def __getArtistFromDB(self,name):
        return self.dbSession.query(dbArtist).filter(dbArtist.name == name).first()

    def __getLabelFromDB(self, name):
        return self.dbSession.query(dbLabel).filter(dbLabel.name == name).first()

    def __getReleasesForArtistFromDB(self, artist):
        return None

    def __saveReleasesForArtistToDB(self, artist):
        return None

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
            if self.allMusicSearcher.IsActive:
                artist = artist.mergeWithArtist(self.allMusicSearcher.lookupArtist(name))
            if artist:
                # Fetch images with only urls
                if artist.images:
                    imageSearcher = ImageSearcher()
                    for image in artist.images:
                        if not image.image and image.url:
                            image.image = imageSearcher.getImageBytesForUrl(image.url)
                self.cache[name] = artist
                #   self.dbSession.expunge(artist)
                # self.dbSession.add(artist)
                #   self.dbSession.commit()
                result = artist
        foundArtistName = None
        if result:
            foundArtistName = result.name
        self.logger.debug("searchForArtist Name [" + name + "] Found [" + str(foundArtistName) + "]")
        return result

    def _mergeReleaseLists(self, left, right):
        if left and not right:
            return left
        elif not left and right:
            return right
        else:
            mergedReleases = []
            # Merge or add the left side
            for release in left:
                rRelease = ([r for r in right if isEqual(r.title, release.title)])
                if rRelease:
                    mergedReleases.append(release.mergeWithRelease(rRelease[0]))
                else:
                    mergedReleases.append(release)
            # Merge the right with the new merged list
            for release in right:
                rRelease = ([r for r in mergedReleases if isEqual(r.title, release.title)])
                if not rRelease:
                    mergedReleases.append(release)
            return mergedReleases


    def searchForArtistReleases(self, artist, titleFilter=None):
        result = self.__getReleasesForArtistFromDB(artist)
        if not result:
            releases = []
            iTunesSearcher = iTunes(self.referer)
            if iTunesSearcher.IsActive:
                releases = iTunesSearcher.searchForRelease(artist, titleFilter)
            mbSearcher = MusicBrainz(self.referer)
            if mbSearcher.IsActive:
                releases = self._mergeReleaseLists(releases, mbSearcher.searchForRelease(artist, titleFilter))
            lastFMSearcher = LastFM(self.referer)
            if lastFMSearcher.IsActive:
                mbIdList = [x.musicBrainzId for x in releases if x.musicBrainzId]
                releases = self._mergeReleaseLists(releases,
                lastFMSearcher.lookupReleasesForMusicBrainzIdList(mbIdList))
            spotifySearcher = Spotify(self.referer)
            if spotifySearcher.IsActive:
                releases = self._mergeReleaseLists(releases, spotifySearcher.searchForRelease(artist, titleFilter))
            if self.allMusicSearcher.IsActive:
                releases = self._mergeReleaseLists(releases,
                self.allMusicSearcher.searchForRelease(artist, titleFilter))
            if releases:
                result = releases
                artist.releases = result
                self.__saveReleasesForArtistToDB(artist)
        if titleFilter:
            return ([r for r in result if isEqual(r.title, titleFilter)])
        return result
        pass
