from sqlalchemy import Column, Enum, ForeignKey, Index, Table, Integer, SmallInteger, Boolean, BLOB, String, Date, Text
from sqlalchemy_utils import ScalarListType
from sqlalchemy.orm import relationship
from resources.common import *
from resources.models.ModelBase import Base
from resources.models.Genre import Genre
from resources.models.CollectionRelease import CollectionRelease
from resources.models.ReleaseLabel import ReleaseLabel
from resources.models.ReleaseMedia import ReleaseMedia
from resources.models.UserRelease import UserRelease
from resources.models.Image import Image

releaseGenreTable = Table('releaseGenreTable', Base.metadata,
                          Column('releaseId', Integer, ForeignKey('release.id')),
                          Column('genreId', Integer, ForeignKey('genre.id')),
                          Index("idx_releaseGenreTableReleaseAndGenre", "releaseId", "genreId")
                          )


class Release(Base):
    # This is set to true to indicate the tracks on this Release are physically on other releases
    isVirtual = Column(Boolean(), default=False)
    title = Column(String(250), nullable=False, index=True)
    alternateNames = Column(ScalarListType(separator="|"))
    releaseDate = Column(Date())
    # Calculated when a user rates an artist based on average User Ratings and stored here for performance
    rating = Column(SmallInteger(), nullable=False, default=0)
    # Number of Tracks that should be for all Release Media for this Release
    trackCount = Column(SmallInteger(), nullable=False)
    # Number of Release Media (CDs or LPs) for this Release
    mediaCount = Column(SmallInteger(), default=1)
    thumbnail = Column(BLOB())
    profile = Column(Text())
    releaseType = Column(Enum('Album', 'EP', 'Single', 'Unknown', name='releaseType'), default='Album')
    # Flag if all tracks are found (Complete), missing some tracks (Incomplete),
    #     no Folder Found/Missing All Tracks (Missing) or Missing and Wished for (Wishlist)
    libraryStatus = Column(Enum('Complete', 'Incomplete', 'Missing', 'Wishlist', name='releaseType'), default='Missing')
    iTunesId = Column(String(100))
    amgId = Column(String(100))
    lastFMId = Column(String(100))
    lastFMSummary = Column(Text())
    musicBrainzId = Column(String(100))
    spotifyId = Column(String(100))
    tags = Column(ScalarListType(separator="|"))
    urls = Column(ScalarListType(separator="|"))

    artistId = Column(Integer, ForeignKey("artist.id"))
    genres = relationship(Genre, cascade="all", secondary=releaseGenreTable)
    releaseLabels = relationship(ReleaseLabel, cascade="all, delete-orphan", backref="release")
    media = relationship(ReleaseMedia, cascade="all, delete-orphan", backref="release")
    images = relationship(Image, cascade="all, delete-orphan", backref="release")
    userRatings = relationship(UserRelease, cascade="all, delete-orphan", backref="release")
    collections = relationship(CollectionRelease, cascade="all, delete-orphan", backref="release")


    def get_id(self):
        return self.roadieId

    def isLiveOrCompilation(self):
        """
        Determine if the release is a Live or Compilation release

        """
        return self._isReleaseTypeOf("Live", False) or self._isReleaseTypeOf("Compilation", False)

    def isVariousArtists(self):
        """
        Determine if the release is a Various Artists release
        :return: bool
        """
        return self._isReleaseTypeOf("Various Artist", True)

    def isSoundTrackRecording(self):
        """
        Determine if the release is a SoundTrack release
        :return: bool
        """
        return self._isReleaseTypeOf("Sound Track", True)

    def isCastRecording(self):
        """
        Determine if the release is a Cast Recording release
        :return: bool
        """
        return self._isReleaseTypeOf("Original Broadway Cast", True) or self._isReleaseTypeOf("Original Cast", True)

    def _isReleaseTypeOf(self, releaseType, doCheckTitles=False):
        """
        Determine if the release is a type of the given type
        :return: bool
        """
        releaseType = releaseType.lower()
        try:
            if doCheckTitles:
                if self.artist:
                    if releaseType in self.artist.name.lower():
                        return True
                if releaseType in self.title.lower():
                    return True
                if self.alternateNames:
                    for alternateName in self.alternateNames:
                        if alternateName and (alternateName.lower() == releaseType):
                            return True
            if self.tags:
                for tag in self.tags:
                    if tag and (tag.lower() == releaseType):
                        return True
            if self.genres:
                for genre in self.genres:
                    if genre and (genre.name.lower() == releaseType):
                        return True
        except:
            pass
        return False

    def __unicode__(self):
        return self.title

    def __str__(self):
        return self.title

    def info(self):
        return ("Id [" + str(self.id) + "], RoadieId [" + str(self.roadieId) +
                "], AlternateNames [" + "|".join(self.alternateNames or []) + "], Tags [" + "|".join(self.tags or []) +
                "], MusicBrainzId [" + str(self.musicBrainzId) + "], ITunesId [" + str(self.iTunesId) +
                "], SpotifyId [" + str(self.spotifyId) + "], AmgId [" + str(self.amgId)
                + "],LastFMId [" + str(self.lastFMId) + "], ReleaseDate [" +
                str(self.releaseDate) + "], TrackCount [" + str(self.trackCount) +
                "], Title [" + str(self.title) + "]").encode('ascii', 'ignore').decode('utf-8')

    def mergeWith(self, right):
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
        result.iTunesId = result.iTunesId or right.iTunesId
        result.amgId = result.amgId or right.amgId
        result.lastFMId = result.lastFMId or right.lastFMId
        result.musicBrainzId = result.musicBrainzId or right.musicBrainzId
        result.spotifyId = result.spotifyId or right.spotifyId
        result.lastFMSummary = result.lastFMSummary or right.lastFMSummary
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
                if image not in result.images:
                    result.images.append(image)
        if not result.genres and right.genres:
            result.genres = right.genres
        elif result.genres and right.genres:
            for genre in right.genres:
                if not ([g for g in result.genres if isEqual(g.name, genre.name)]):
                    result.genres.append(genre)
        if not result.releaseLabels and right.releaseLabels:
            result.releaseLabels = right.releaseLabels
        elif result.releaseLabels and right.releaseLabels:
            for releaseLabel in right.releaseLabels:
                if not ([l for l in result.releaseLabels if isEqual(l.label.name, releaseLabel.label.name)]):
                    result.releaseLabels.append(releaseLabel)
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
            result.mediaCount = 0
            for media in result.media:
                result.trackCount += len(media.tracks or [])
                result.mediaCount += 1
        return result


Index("idx_releaseArtistAndTitle", Release.artistId, Release.title, unique=True)
