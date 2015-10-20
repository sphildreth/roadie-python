from enum import IntEnum

from sqlalchemy import Column, ForeignKey, Table, Integer, SmallInteger, String, DateTime
from sqlalchemy_utils import ScalarListType
from sqlalchemy.orm import relationship

from resources.models.ModelBase import Base
from resources.models.PlaylistTrack import PlaylistTrack

trackPlaylistTrackTable = Table('trackPlaylistTrack', Base.metadata,
                                Column('trackId', Integer, ForeignKey('track.id'), index=True),
                                Column('playlisttrackId', Integer, ForeignKey('playlisttrack.id'), index=True))


class TrackStatus(IntEnum):
    Standard = 0
    ProcessorAdded = 1


class Track(Base):

    filePath = Column(String(1000))
    fileName = Column(String(500))
    # File size of the track in bytes
    fileSize = Column(Integer, default=0)
    hash = Column(String(32), unique=True)
    playedCount = Column(Integer, default=0)
    lastPlayed = Column(DateTime())
    partTitles = Column(ScalarListType(separator="|"))
    # This is calculated when a user rates an artist based on average User Ratings and stored here for performance
    rating = Column(SmallInteger(), nullable=False, default=0)
    # This is a random number generated at generation and then used to select random releases
    random = Column(Integer, nullable=False, default=0, index=True)
    musicBrainzId = Column(String(100))
    amgId = Column(String(100))
    spotifyId = Column(String(100))
    title = Column(String(500), nullable=False, index=True)
    trackNumber = Column(SmallInteger(), nullable=False)
    # Seconds long
    duration = Column(Integer)
    tags = Column(ScalarListType(separator="|"))

    releaseMediaId = Column(Integer, ForeignKey("releasemedia.id"), index=True)
    playlists = relationship(PlaylistTrack, secondary=trackPlaylistTrackTable)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.hash == other.hash
        return False

    def __unicode__(self):
        return self.title

    def __str(self):
        return "[" + str(self.trackNumber) + "] " + self.title + " [" + str(self.duration) + "]"

    def info(self):
        return "Id [" + str(self.id) + "], RoadieId [" + str(self.roadieId) + "], MusicBrainzId [" + str(
            self.musicBrainzId) \
               + "], Title [" + str(self.title) + "],TrackNumber [" + str(self.trackNumber) \
               + "], Duration [" + str(self.duration) + "]"
