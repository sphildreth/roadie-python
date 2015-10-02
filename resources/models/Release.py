from sqlalchemy import Column, ForeignKey, Table, Integer, SmallInteger, Boolean, BLOB, String, Date
from sqlalchemy_utils import ScalarListType
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from models.ModelBase import ModelBase

Base = declarative_base()

releaseGenreTable = Table('releaseGenreTable', Base.metadata,
                          Column('releaseId', Integer, ForeignKey('release.id')),
                          Column('genreId', Integer, ForeignKey('genre.id')))


class Release(ModelBase):
    __tablename__ = "release"

    isVirtual = Column(Boolean(), default=False)
    title = Column(String(500), nullable=False, index=True)
    alternateNames = Column(ScalarListType())
    releaseDate = Column(Date())
    # Calculated when a user rates an artist based on average User Ratings and stored here for performance
    rating = Column(SmallInteger(), nullable=False)
    # A random number generated at generation and then used to select random releases
    random = Column(Integer(), nullable=False)
    # Number of Tracks that should be for all Release Media for this Release
    trackCount = Column(SmallInteger(), nullable=False)
    # Number of Release Media (CDs or LPs) for this Release
    mediaCount = Column(SmallInteger(), default=1)
    thumbnail = Column(BLOB())
    profile = Column(String(2000))
    coverUrl = Column(String(500))
    iTunesId = Column(String(100))
    lastFMId = Column(String(100))
    musicBrainzId = Column(String(100))
    spotifyId = Column(String(100))
    tags = Column(ScalarListType())
    urls = Column(ScalarListType())

    artistId = Column(Integer(), ForeignKey("artist.id"), index=True)
    genres = relationship("Genre", secondary=releaseGenreTable)
    labels = relationship("ReleaseLabel", backref="release")
    media = relationship("ReleaseMedia", backref="release")
    images = relationship("Image")

    def __init__(self, title, releaseDate, trackCount, coverUrl):
        self.title = title
        self.releaseDate = releaseDate
        self.trackCount = trackCount
        self.coverUrl = coverUrl

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
