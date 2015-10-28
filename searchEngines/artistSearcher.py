import hashlib
import io
import photohash
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


class ArtistSearcher(object):
    """
    Query Enabled Search Engines and Find Artist Information and aggregate results.
    """
    allMusicSearcher = None
    spotifySearcher = None
    mbSearcher = None
    lastFMSearcher = None
    imageSearcher = None
    iTunesSearcher = None

    artistThumbnailSize = 160, 160
    releaseThumbnailSize = 80, 80

    cache = dict()

    imageCache = dict()

    def __init__(self, referer=None):
        self.referer = referer
        if not self.referer or self.referer.startswith("http://localhost"):
            self.referer = "http://github.com/sphildreth/roadie"
        self.logger = Logger()
        self.allMusicSearcher = AllMusicGuide(self.referer)
        self.spotifySearcher = Spotify(self.referer)
        self.mbSearcher = MusicBrainz(self.referer)
        self.lastFMSearcher = LastFM(self.referer)
        self.imageSearcher = ImageSearcher()
        self.iTunesSearcher = iTunes(self.referer)

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
        try:
            startTime = arrow.utcnow().datetime
            artist = Artist(name=name)
            artist.random = random.randint(1, 9999999)
            artist.roadieId = str(uuid.uuid4())
            if self.iTunesSearcher.IsActive:
                artist = artist.mergeWithArtist(self.iTunesSearcher.lookupArtist(name))
            if self.mbSearcher.IsActive:
                artist = artist.mergeWithArtist(self.mbSearcher.lookupArtist(name))
            if self.lastFMSearcher.IsActive:
                artist = artist.mergeWithArtist(self.lastFMSearcher.lookupArtist(name))
            if self.spotifySearcher.IsActive:
                artist = artist.mergeWithArtist(self.spotifySearcher.lookupArtist(name))
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
                            image.signature = image.averageHash()
                            images.append(image)
                    if images:
                        dedupedImages = []
                        imageSignatures = []
                        for image in images:
                            if image.signature not in imageSignatures:
                                imageSignatures.append(image.signature)
                                dedupedImages.append(image)
                        artist.images = dedupedImages
                        if not artist.thumbnail and firstImageInImages:
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
                    if cleanedArtistName != artist.name.lower().strip() and \
                            cleanedArtistName not in artist.alternateNames:
                        artist.alternateNames.append(cleanedArtistName)
                if not artist.bioContext:
                    try:
                        artist.bioContext = wikipedia.summary(artist.name)
                    except:
                        pass

                self.cache[name] = artist
            elapsedTime = arrow.utcnow().datetime - startTime
            printableName = name.encode('ascii', 'ignore').decode('utf-8')
            self.logger.debug("searchForArtist Elapsed Time [" + str(elapsedTime) + "] Name [" + printableName
                              + "] Found [" + (artist.name if artist else "")
                              .encode('ascii', 'ignore').decode('utf-8') + "]")
            return artist
        except:
            self.logger.exception("Error In searchForArtist")
        return None

    def _mergeReleaseLists(self, left, right):
        if left and not right:
            return left
        elif not left and right:
            return right
        elif not left and not right:
            return []
        else:
            mergeReleaseListsStart = arrow.utcnow()
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
            mergedReleaseElapsed = arrow.utcnow() - mergeReleaseListsStart
            self.logger.debug("= MergeReleaseLists left size [" + str(len(left)) + "], right size [" + str(
                len(right)) + "] Elapsed Time [" + str(mergedReleaseElapsed) + "]")
            return mergedReleases

    def searchForArtistReleases(self, artist, artistReleaseImages, titleFilter=None):
        """
        Using the given populated Artist find all releases, with an optional filter

        :param artist: Artist
                       Artist to find releases for
        :param artistReleaseImages: list
                                    Collection if image signatures for Artist for deduping
        :param titleFilter: String
                            Optional filter of release Title to only include in results
        :return: iterable Release
                 Collection of releases found for artist
        """
        if not artist:
            return None
        try:
            startTime = arrow.utcnow().datetime
            releases = []
            if self.iTunesSearcher.IsActive:
                releases = self._mergeReleaseLists(releases, self.iTunesSearcher.searchForRelease(artist, titleFilter))
            if self.mbSearcher.IsActive:
                releases = self._mergeReleaseLists(releases, self.mbSearcher.searchForRelease(artist, titleFilter))
            if self.lastFMSearcher.IsActive and releases:
                mbIdList = [x.musicBrainzId for x in releases if x.musicBrainzId]
                if mbIdList:
                    releases = self._mergeReleaseLists(releases,
                                                       self.lastFMSearcher.lookupReleasesForMusicBrainzIdList(artist,
                                                                                                              mbIdList))
            if self.spotifySearcher.IsActive:
                releases = self._mergeReleaseLists(releases, self.spotifySearcher.searchForRelease(artist, titleFilter))
            if releases:
                self.logger.debug(
                    "searchForArtistReleases Found [" + str(len(releases)) + "] For title [" + str(titleFilter) + "]")
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
                                image.image = self.getImageForUrl(image.url)
                            if image.image:
                                image.signature = image.averageHash()
                                images.append(image)
                        if images:
                            dedupedImages = []
                            imageSignatures = artistReleaseImages
                            for image in images:
                                if image.signature not in imageSignatures:
                                    firstImageInImages = firstImageInImages or image.image
                                    imageSignatures.append(image.signature)
                                    dedupedImages.append(image)
                            release.images = dedupedImages
                            if not release.thumbnail and firstImageInImages:
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
            elapsedTime = arrow.utcnow().datetime - startTime
            self.logger.debug("searchForArtistReleases ElapseTime [" + str(elapsedTime) + "]")
            return releases
        except:
            self.logger.exception("Error In searchForArtistReleases")
            pass
        return None

    def getImageForUrl(self, url):
        if url not in self.imageCache:
            self.imageCache[url] = self.imageSearcher.getImageBytesForUrl(url)
            self.logger.debug("= Downloading Image [" + str(url) + "]")
        return self.imageCache[url]
