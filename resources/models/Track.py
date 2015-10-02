from sqlalchemy import Column, ForeignKey, Integer, SmallInteger, String, DateTime
from sqlalchemy_utils import ScalarListType
from sqlalchemy.ext.declarative import declarative_base

from models.ModelBase import ModelBase

Base = declarative_base()


class Track(ModelBase):
    __tablename__ = "track"

    fileName = Column(String(500), nullable=False)
    filePath = Column(String(1000), nullable=False)
    hash = Column(String(32), unique=True)
    playedCount = Column(Integer(), default=0)
    lastPlayed = Column(DateTime())
    partTitles = Column(ScalarListType())
    # This is calculated when a user rates an artist based on average User Ratings and stored here for performance
    rating = Column(SmallInteger(), nullable=False)
    # This is a random number generated at generation and then used to select random releases
    random = Column(Integer(), nullable=False)
    musicBrainzId = Column(String(100))
    spotifyId = Column(String(100))
    title = Column(String(500), nullable=False, index=True)
    trackNumber = Column(SmallInteger(), nullable=False)
    # Seconds long
    duration = Column(Integer())
    tags = Column(ScalarListType())

    releaseMediaId = Column(Integer(), ForeignKey("releaseMedia.id"), index=True)

    def __init__(self, title):
        self.title = title

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.hash == other.hash
        return False

    def __unicode__(self):
        return self.title

    def info(self):
        return "Id [" + str(self.id) + "], RoadieId [" + str(self.roadieId) + "], MusicBrainzId [" + str(
            self.musicBrainzId) \
               + "], Title [" + str(self.title) + "], ReleaseMediaNumber[" + str(
            self.releaseMediaNumber) + "], TrackNumber [" + str(self.trackNumber) \
               + "], Duration [" + str(self.duration) + "]"
