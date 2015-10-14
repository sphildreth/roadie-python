import random
import uuid

from resources.common import *
from resources.logger import Logger
from searchEngines.imageSearcher import ImageSearcher
from searchEngines.musicBrainz import MusicBrainz
from searchEngines.iTunes import iTunes
from searchEngines.lastFM import LastFM
from searchEngines.spotify import Spotify
from searchEngines.allMusic import AllMusicGuide
from searchEngines.models.Artist import Artist

from resources.models.ModelBase import ModelBase


class ArtistSearcher(object):
    """
    Query Enabled Search Engines and Find Artist Information and aggregate results.
    """
    allMusicSearcher = None

    cache = dict()

    def __init__(self, referer=None):
        self.referer = referer
        if not self.referer or self.referer.startswith("http://localhost"):
            self.referer = "http://github.com/sphildreth/roadie"
        self.logger = Logger()
        self.allMusicSearcher = AllMusicGuide(self.referer)

    def searchForArtist(self, name):
        """
        Perform a search in all enabled search engines and return an aggregate Artist for the given Artist name
        :param name: String
                     Name of the Artist to find
        :return: Artist
                 Populated Artist or None if error or not found
        """
        if not name:
            return None
        if name in self.cache:
            return self.cache[name]
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
        self.logger.debug("searchForArtist Name [" + name + "] Found [" + (artist.name if artist else "") + "]")
        return artist

    @staticmethod
    def _mergeReleaseLists(left, right):
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
        """
        Using the given populated Artist find all releases, with an optional filter

        :param artist: Artist
                       Artist to find releases for
        :param titleFilter: String
                            Optional filter of release Title to only include in results
        :return: iterable Release
                 Collection of releases found for artist
        """
        if not artist:
            return None
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
        if releases:
            artist.releases = releases
        if titleFilter:
            return [r for r in releases if isEqual(r.title, titleFilter)]
        return releases
