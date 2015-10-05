from sqlalchemy import Column, Enum, ForeignKey, Table, Integer, SmallInteger, Boolean, BLOB, String, Date, Text
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
    lastFMSummary = Column(Text())
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

