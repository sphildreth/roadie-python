import random
from enum import Enum
from resources.common import *
from searchEngines.models.ModelBase import ModelBase


class ArtistType(Enum):
    Unknown = 0
    Person = 1
    Group = 2
    Orchestra = 3
    Choir = 4
    Character = 5
    Other = 6


class Artist(ModelBase):
    name = None
    sortName = None
    # This is calculated when a user rates an artist based on average User Ratings and stored here for performance
    rating = 0
    # This is a random number generated at generation and then used to select random releases
    random = random.randint(1, 9999999)
    realName = None
    musicBrainzId = None
    iTunesId = None
    amgId = None
    spotifyId = None
    thumbnail = None
    profile = None
    birthDate = None
    beginDate = None
    endDate = None
    artistType = ArtistType.Unknown
    bioContext = None
    isniList = []

    releases = []
    images = []
    genres = []
    associatedArtists = []

    def __init__(self, name):
        self.name = name
        super(Artist, self).__init__()

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    def info(self):
        trackCount = 0
        mediaCount = 0
        labelNames = []
        if self.releases:
            for release in self.releases:
                if release.media:
                    if release.labels:
                        for releaseLabel in release.labels:
                            labelNames.append(releaseLabel.label.name + " (" + str(releaseLabel.roadieId) + ")")
                    for media in release.media:
                        trackCount += len(media.tracks)
                        mediaCount += 1
        return "RoadieId [" + str(self.roadieId) + "], MusicBrainzId [" + str(
            self.musicBrainzId) + "], " + \
               "AlternateNames [" + "|".join(self.alternateNames or []) + "], Tags [" + "|".join(self.tags or []) + \
               "], ITunesId [" + str(self.iTunesId) + "], AmgId [" + str(self.amgId) + "], SpotifyId [" + str(
            self.spotifyId) + "], Name [" + str(self.name) + "], SortName [" + str(self.sortName) + \
               "] Releases [" + str(len(self.releases or [])) + "] Labels [" + "|".join(labelNames) + "] Media [" + str(
            mediaCount) + "] Tracks [" + str(trackCount) + "] Images [" + str(
            len(self.images or [])) + "] Genres [" + \
               "|".join(map(lambda x: x.name, self.genres or [])) + "] Associated Artist [" + str(
            len(self.associatedArtists or [])) + "]"

    def mergeWithArtist(self, right):
        """

        :type right: Artist
        """
        result = self
        if not right:
            return result

        if not result.name and right.name:
            result.name = right.name
        elif right.name and not isEqual(result.name, right.name):
            if not result.alternateNames:
                result.alternateNames = []
            if not isInList(result.alternateNames, right.name):
                result.alternateNames.append(right.name)
        if not result.sortName and right.sortName:
            result.sortName = right.sortName
        elif right.sortName and not isEqual(result.sortName, right.sortName):
            if not result.alternateNames:
                result.alternateNames = []
            if not isInList(result.alternateNames, right.sortName):
                result.alternateNames.append(right.sortName)
        result.musicBrainzId = result.musicBrainzId or right.musicBrainzId
        result.iTunesId = result.iTunesId or right.iTunesId
        result.amgId = result.amgId or right.amgId
        result.spotifyId = result.spotifyId or right.spotifyId
        result.birthDate = result.birthDate or right.birthDate
        result.beginDate = result.beginDate or right.beginDate
        result.endDate = result.endDate or right.endDate
        if not result.artistType or result.artistType == ArtistType.Unknown and right.artistType:
            result.artistType = right.artistType

        if not result.images and right.images:
            result.images = right.images
        elif result.images and right.images:
            for image in right.images:
                if image not in result.images:
                    result.images.append(image)

        result.bioContext = result.bioContext or right.bioContext
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
        if not result.isniList and right.isniList:
            result.isniList = right.isniList
        elif result.isniList and right.isniList:
            for isni in right.isniList:
                if not isInList(result.isniList, isni):
                    result.isniList.append(isni)
        if not result.releases and right.releases:
            result.releases = right.releases
        elif result.releases and right.releases:
            mergedReleases = []
            for release in result.releases:
                rightRelease = ([r for r in right.releases if isEqual(r.title, release.title)])
                if rightRelease:
                    mergedReleases.append(release.mergeWithRelease(rightRelease[0]))
                else:
                    mergedReleases.append(release)
            result.releases = mergedReleases
        if not result.genres and right.genres:
            result.genres = right.genres
        elif result.genres and right.genres:
            for genre in right.genres:
                if not isInList(result.genres, genre):
                    result.genres.append(genre)
        return result
