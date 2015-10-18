import io
import random
import uuid
import wikipedia

from PIL import Image

from resources.common import *
from resources.logger import Logger
from searchEngines.imageSearcher import ImageSearcher
from searchEngines.musicBrainz import MusicBrainz
from searchEngines.iTunes import iTunes
from searchEngines.lastFM import LastFM
from searchEngines.spotify import Spotify
from searchEngines.allMusic import AllMusicGuide
from searchEngines.models.Artist import Artist
from searchEngines.models.Image import Image as ArtistImage

from resources.models.ModelBase import ModelBase


class ArtistSearcher(object):
    """
    Query Enabled Search Engines and Find Artist Information and aggregate results.
    """
    allMusicSearcher = None

    artistThumbnailSize = 160, 160
    releaseThumbnailSize = 80, 80

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
            # Fetch images with only urls, remove any with neither URL or BLOB
            if artist.images:
                images = []
                imageSearcher = ImageSearcher()
                firstImageInImages = None
                for image in artist.images:
                    if not image.image and image.url:
                        image.image = imageSearcher.getImageBytesForUrl(image.url)
                    if image.image:
                        firstImageInImages = firstImageInImages or image.image
                        images.append(image)
                artist.images = images
                if not artist.thumbnail:
                    try:
                        img = Image.open(io.BytesIO(firstImageInImages)).convert('RGB')
                        img.thumbnail(self.artistThumbnailSize)
                        b = io.BytesIO()
                        img.save(b, "JPEG")
                        artist.thumbnail = b.getvalue()
                    except:
                        pass
            # Add special search names to alternate names
            if not artist.alternateNames:
                artist.alternateNames = []
            if artist.name not in artist.alternateNames:
                cleanedArtistName = createCleanedName(artist.name)
                if cleanedArtistName != artist.name.lower().strip() and cleanedArtistName not in artist.alternateNames:
                    artist.alternateNames.append(cleanedArtistName)
            if not artist.bioContext:
                try:
                    artist.bioContext = wikipedia.summary(artist.name)
                except:
                    pass

            self.cache[name] = artist
        printableName = name.encode('ascii', 'ignore').decode('utf-8')
        self.logger.debug("searchForArtist Name [" + printableName + "] Found [" + (artist.name if artist else "").encode('ascii', 'ignore').decode('utf-8') + "]")
        return artist

    @staticmethod
    def _mergeReleaseLists(left, right):
        if left and not right:
            return left
        elif not left and right:
            return right
        elif not left and not right:
            return []
        else:
            mergedReleases = left
            # Merge the right to the result
            for rRelease in right:
                foundRightInMerged = False
                for mRelease in mergedReleases:
                    if mRelease == rRelease:
                        mRelease.mergeWithRelease(rRelease)
                        foundRightInMerged = True
                        break
                if not foundRightInMerged:
                    mergedReleases.append(rRelease)
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
            releases = self._mergeReleaseLists(releases, iTunesSearcher.searchForRelease(artist, titleFilter))
        mbSearcher = MusicBrainz(self.referer)
        if mbSearcher.IsActive:
            releases = self._mergeReleaseLists(releases, mbSearcher.searchForRelease(artist, titleFilter))
        lastFMSearcher = LastFM(self.referer)
        if lastFMSearcher.IsActive:
            mbIdList = [x.musicBrainzId for x in releases if x.musicBrainzId]
            if mbIdList:
                releases = self._mergeReleaseLists(releases, lastFMSearcher.lookupReleasesForMusicBrainzIdList(mbIdList))
        spotifySearcher = Spotify(self.referer)
        if spotifySearcher.IsActive:
            releases = self._mergeReleaseLists(releases, spotifySearcher.searchForRelease(artist, titleFilter))
        if releases:
            imageSearcher = ImageSearcher()
            for release in releases:
                if release.coverUrl:
                    coverImage = ArtistImage(release.coverUrl)
                    if coverImage not in release.images:
                        release.images.append(coverImage)
                # Fetch images with only urls, remove any with neither URL or BLOB
                if release.images:
                    images = []
                    firstImageInImages = None
                    for image in release.images:
                        if not image.image and image.url:
                            image.image = imageSearcher.getImageBytesForUrl(image.url)
                        if image.image:
                            firstImageInImages = firstImageInImages or image.image
                            images.append(image)
                    release.images = images
                    if not release.thumbnail:
                        try:
                            img = Image.open(io.BytesIO(firstImageInImages)).convert('RGB')
                            img.thumbnail(self.releaseThumbnailSize)
                            b = io.BytesIO()
                            img.save(b, "JPEG")
                            release.thumbnail = b.getvalue()
                        except:
                            pass
        if titleFilter and releases:
            filteredReleases = []
            cleanedTitleFilter = createCleanedName(titleFilter)
            for release in releases:
                if isEqual(release.title, titleFilter) or cleanedTitleFilter in release.alternateNames:
                    filteredReleases.append(release)
            releases = filteredReleases
        return releases
