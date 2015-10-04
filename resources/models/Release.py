from sqlalchemy import Column, Enum, ForeignKey, Table, Integer, SmallInteger, Boolean, BLOB, String, Date
from sqlalchemy_utils import ScalarListType
from sqlalchemy.orm import relationship

from resources.models.ModelBase import Base
from resources.models.Genre import Genre
from resources.models.ReleaseLabel import ReleaseLabel
from resources.models.ReleaseMedia import ReleaseMedia
from resources.models.Image import Image

releaseGenreTable = Table('releaseGenreTable', Base.metadata,
                          Column('releaseId', Integer, ForeignKey('release.id'), index=True),
                          Column('genreId', Integer, ForeignKey('genre.id')))


class Release(Base):

    isVirtual = Column(Boolean(), default=False)
    title = Column(String(500), nullable=False, index=True)
    alternateNames = Column(ScalarListType())
    releaseDate = Column(Date())
    # Calculated when a user rates an artist based on average User Ratings and stored here for performance
    rating = Column(SmallInteger(), nullable=False, default=0)
    # A random number generated at generation and then used to select random releases
    random = Column(Integer, nullable=False, default=0, index=True)
    # Number of Tracks that should be for all Release Media for this Release
    trackCount = Column(SmallInteger(), nullable=False)
    # Number of Release Media (CDs or LPs) for this Release
    mediaCount = Column(SmallInteger(), default=1)
    thumbnail = Column(BLOB())
    profile = Column(String(2000))
    coverUrl = Column(String(500))
    releaseType = Column(Enum('Album', 'EP', 'Single', name='releaseType'), default='Album')
    # Flag if all tracks are found (Complete), missing some tracks (Incomplete),
    #     no Folder Found/Missing All Tracks (Missing) or Missing and Wished for (Wishlist)
    libraryStatus = Column(Enum('Complete', 'Incomplete', 'Missing', 'Wishlist', name='releaseType'), default='Missing')
    iTunesId = Column(String(100))
    amgId = Column(String(100))
    lastFMId = Column(String(100))
    musicBrainzId = Column(String(100))
    spotifyId = Column(String(100))
    tags = Column(ScalarListType())
    urls = Column(ScalarListType())

    artistId = Column(Integer, ForeignKey("artist.id"), index=True)
    genres = relationship(Genre, secondary=releaseGenreTable)
    labels = relationship(ReleaseLabel, backref="release")
    media = relationship(ReleaseMedia, backref="release")
    images = relationship(Image)

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

    def mergeWithArtist(self, right):
        """

        :type right: Release
        """
        result = self
        if not right:
            return result
        if not result.title and right.title:
            result.title = right.title
        elif right.title and result.title.lower().strip() != right.title.lower().strip():
            if not result.alternateNames:
                result.alternateNames = []
            if not right.title in result.alternateNames:
                result.alternateNames.append(right.title)
        result.releaseDate = result.releaseDate or right.releaseDate
        result.profile = result.profile or right.profile
        result.thumbnail = result.thumbnail or right.thumbnail
        result.coverUrl = result.coverUrl or right.coverUrl
        if not result.releaseType or result.releaseType.lower().strip() == "unknown" and right.releaseType:
            result.releaseType = right.releaseType
        if not result.libraryStatus or result.libraryStatus.lower().strip() == "unknown" and right.libraryStatus:
            result.libraryStatus = right.libraryStatus
        result.iTunesId = result.iTunesId or right.iTunesId
        result.amgId = result.amgId or right.amgId
        result.lastFMId = result.lastFMId or right.lastFMId
        result.musicBrainzId = result.musicBrainzId or right.musicBrainzId
        result.spotifyId = result.spotifyId or right.spotifyId
        if not result.tags and right.tags:
            result.tags = right.tags
        elif result.tags and right.tags:
            for tag in right.tags:
                if not tag in result.tags:
                    result.tags.append(tag)
        if not result.alternateNames and right.alternateNames:
            result.alternateNames = right.alternateNames
        elif result.alternateNames and right.alternateNames:
            for alternateName in right.alternateNames:
                if not alternateName in result.alternateNames:
                    result.alternateNames.append(alternateName)
        if not result.urls and right.urls:
            result.urls = right.urls
        elif result.urls and right.urls:
            for url in right.urls:
                if not url in result.urls:
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
                if not genre in result.genres:
                    result.genres.append(genre)
        if not result.labels and right.labels:
            result.labels = right.labels
        elif result.labels and right.labels:
            for label in right.labels:
                if not label in result.labels:
                    result.labels.append(label)
        if not result.images and right.images:
            result.images = right.images
        elif result.images and right.images:
            for image in right.images:
                if not image in result.images:
                    result.images.append(image)

        if not result.media and right.media:
            result.media = right.media
        elif result.media and right.media:
            for media in right.media:
                if not media in result.media:
                    result.media.append(media)
        if result.media:
            result.trackCount = 0
            for media in result.media:
                result.trackCount = result.trackCount + len(media.tracks or [])

        return result
