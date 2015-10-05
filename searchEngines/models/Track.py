import random

from resources.common import *
from searchEngines.models.ModelBase import ModelBase


class Track(ModelBase):
    fileName = None
    filePath = None
    hash = None
    playedCount = 0
    lastPlayed = None
    partTitles = []
    # This is calculated when a user rates an artist based on average User Ratings and stored here for performance
    rating = 0
    # This is a random number generated at generation and then used to select random releases
    random = random.randint(1, 9999999)
    musicBrainzId = None
    amgId = None
    spotifyId = None
    title = None
    trackNumber = 0
    # Seconds long
    duration = 0

    releaseMedia = None
    releaseMediaId = 0

    def __init__(self, title):
        self.title = title
        super(Track, self).__init__()

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.hash == other.hash
        return False

    def __unicode__(self):
        return self.title

    def __str(self):
        return "[" + str(self.trackNumber) + "] " + str(self.title) + " [" + str(self.duration) + "]"

    def info(self):
        return "Id [" + str(self.id) + "], RoadieId [" + str(self.roadieId) + "], MusicBrainzId [" + str(
            self.musicBrainzId) \
               + "], Title [" + str(self.title) + "], ReleaseMediaNumber[" + str(
            self.releaseMediaNumber) + "], TrackNumber [" + str(self.trackNumber) \
               + "], Duration [" + str(self.duration) + "]"

    def mergeWithTrack(self, right):

        """

        :type right: Track
        """
        result = self
        if not right:
            return result

        result.fileName = result.fileName or right.fileName
        result.filePath = result.filePath or right.filePath
        result.hash = result.hash or right.hash
        result.playedCount = result.playedCount or right.playedCount
        result.lastPlayed = result.lastPlayed or right.lastPlayed
        result.partTitles = result.partTitles or right.partTitles
        result.musicBrainzId = result.musicBrainzId or right.musicBrainzId
        result.amgId = result.amgId or right.amgId
        result.spotifyId = result.spotifyId or right.spotifyId
        result.title = result.title or right.title
        result.trackNumber = result.trackNumber or right.trackNumber
        result.duration = result.duration or right.duration
        result.releaseMediaId = result.releaseMediaId or right.releaseMediaId

        if not result.tags and right.tags:
            result.tags = right.tags
        elif result.tags and right.tags:
            for tag in right.tags:
                if not isInList(result.tags, tag):
                    result.tags.append(tag)
        return result
