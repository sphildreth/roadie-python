import random
from enum import Enum

from resources.common import *
from searchEngines.models.ModelBase import ModelBase


class ReleaseType(Enum):
    Unknown = 0
    Complete = 1
    Incomplete = 2
    Missing = 3
    Wishlist = 4


class Release(ModelBase):
    isVirtual = False
    title = None
    alternateNames = []
    releaseDate = None
    # Calculated when a user rates an artist based on average User Ratings and stored here for performance
    rating = 0
    # A random number generated at generation and then used to select random releases
    random = random.randint(1, 9999999)
    # Number of Tracks that should be for all Release Media for this Release
    trackCount = 0
    # Number of Release Media (CDs or LPs) for this Release
    mediaCount = 0
    thumbnail = None
    profile = None
    coverUrl = None
    releaseType = ReleaseType.Unknown
    iTunesId = None
    amgId = None
    lastFMId = None
    musicBrainzId = None
    spotifyId = None

    artistId = None
    genres = []
    labels = []
    media = []
    images = []

    def __init__(self, title, releaseDate=None):
        self.title = title
        self.releaseDate = releaseDate

    def isLiveOrCompilation(self):
        """
        Determine if the release is a Live or Compilation album

        """
        try:
            if self.tags:
                for tag in self.tags:
                    if tag and (tag.lower() == "live" or tag.lower() == "compilation"):
                        return True
            if self.genres:
                for genre in self.genres:
                    if genre and (genre.name.lower() == "live" or genre.name.lower() == "compilation"):
                        return True
        except:
            pass
        return False

    def __unicode__(self):
        return self.title

    def info(self):
        return "Id [" + str(self.id) + "], RoadieId [" + str(self.roadieId) + "], MusicBrainzId [" + str(
            self.musicBrainzId) + "], ITunesId [" + str(self.iTunesId) + \
               "], LastFMId [" + str(self.lastFMId) + "], ReleaseDate [" + str(
            self.releaseDate) + "], TrackCount [" + str(self.trackCount) + "], Title [" + str(self.title) + "]"

    def mergeWithRelease(self, right):
        """

        :type right: Release
        """
        result = self
        if not right:
            return result
        result.isVirtual = result.isVirtual or right.isVirtual
        if not result.title and right.title:
            result.title = right.title
        elif right.title and not isEqual(result.title, right.title):
            if not result.alternateNames:
                result.alternateNames = []
            if not isInList(result.alternateNames, right.title):
                result.alternateNames.append(right.title)
        result.releaseDate = result.releaseDate or right.releaseDate
        result.profile = result.profile or right.profile
        result.thumbnail = result.thumbnail or right.thumbnail
        result.coverUrl = result.coverUrl or right.coverUrl
        if not result.releaseType or result.releaseType == ReleaseType.Unknown and right.releaseType:
            result.releaseType = right.releaseType
        result.iTunesId = result.iTunesId or right.iTunesId
        result.amgId = result.amgId or right.amgId
        result.lastFMId = result.lastFMId or right.lastFMId
        result.musicBrainzId = result.musicBrainzId or right.musicBrainzId
        result.spotifyId = result.spotifyId or right.spotifyId
        if not result.tags and right.tags:
            result.tags = right.tags
        elif result.tags and right.tags:
            for tag in right.tags:
                if not isInList(result.tags, tag):
                    result.tags.append(tag)
        if not result.alternateNames and right.alternateNames:
            result.alternateNames = right.alternateNames
        elif result.alternateNames and right.alternateNames:
            for alternateName in right.alternateNames:
                if not isInList(result.alternateNames, alternateName):
                    result.alternateNames.append(alternateName)
        if not result.urls and right.urls:
            result.urls = right.urls
        elif result.urls and right.urls:
            for url in right.urls:
                if not isInList(result.urls, url):
                    result.urls.append(url)
        if not result.images and right.images:
            result.images = right.images
        elif result.images and right.images:
            for image in right.images:
                if not image in result.images:
                    result.images.append(image)
        if not result.genres and right.genres:
            result.genres = right.genres
        elif result.genres and right.genres:
            for genre in right.genres:
                if not isInList(result.genres, genre):
                    result.genres.append(genre)
        if not result.labels and right.labels:
            result.labels = right.labels
        elif result.labels and right.labels:
            for releaseLabel in right.labels:
                if not ([l for l in result.labels if isEqual(l.label.name, releaseLabel.label.name)]):
                    result.labels.append(releaseLabel)
        if not result.images and right.images:
            result.images = right.images
        elif result.images and right.images:
            for image in right.images:
                if not image in result.images:
                    result.images.append(image)
        if not result.media and right.media:
            result.media = right.media
        elif result.media and right.media:
            mergedMedia = []
            for media in result.media:
                rightMedia = [m for m in right.media if m.releaseMediaNumber == media.releaseMediaNumber]
                if rightMedia:
                    mergedMedia.append(media.mergeWithReleaseMedia(rightMedia[0]))
                else:
                    mergedMedia.append(media)
            result.media = mergedMedia
        if result.media:
            result.trackCount = 0
            for media in result.media:
                result.trackCount = result.trackCount + len(media.tracks or [])
        return result
