import os
from enum import IntEnum

from sqlalchemy import Column, ForeignKey, Table, Index, Integer, SmallInteger, String, DateTime
from sqlalchemy_utils import ScalarListType
from sqlalchemy.orm import relationship

from resources.models.ModelBase import Base
from resources.models.PlaylistTrack import PlaylistTrack
from resources.models.UserTrack import UserTrack

trackPlaylistTrackTable = Table('trackPlaylistTrack', Base.metadata,
                                Column('trackId', Integer, ForeignKey('track.id'), index=True),
                                Column('playlisttrackId', Integer, ForeignKey('playlisttrack.id'), index=True))


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
    musicBrainzId = Column(String(100))
    amgId = Column(String(100))
    spotifyId = Column(String(100))
    title = Column(String(250), nullable=False, index=True)
    alternateNames = Column(ScalarListType(separator="|"))
    trackNumber = Column(SmallInteger(), nullable=False)
    # Seconds long
    duration = Column(Integer)
    tags = Column(ScalarListType(separator="|"))

    releaseMediaId = Column(Integer, ForeignKey("releasemedia.id"))
    playlists = relationship(PlaylistTrack, secondary=trackPlaylistTrackTable, backref="track")
    userRatings = relationship(UserTrack, backref="track")

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.hash == other.hash
        return False

    def __unicode__(self):
        return self.title

    def __str__(self):
        return "[" + str(self.trackNumber) + "] " + self.title + " [" + str(self.duration) + "]"

    def info(self):
        return ("Id [" + str(self.id) + "], RoadieId [" + str(self.roadieId) + "], MusicBrainzId [" + str(
            self.musicBrainzId) + ", Hash [" + self.hash + "] " +
               + "], Title [" + str(self.title) + "],TrackNumber [" + str(self.trackNumber)
               + "], Duration [" + str(self.duration) + "]").encode('ascii', 'ignore').decode('utf-8')

    def fullPath(self):
        # path = track.FilePath
        # if trackPathReplace:
        #     for rpl in trackPathReplace:
        #         for key, val in rpl.items():
        #             path = path.replace(key, val)

        # if not self.trackPathReplace:
        #     self.trackPathReplace = self.getTrackPathReplace()
        # if self.trackPathReplace:
        #     for rpl in self.trackPathReplace:
        #         for key, val in rpl.items():
        #             path = path.replace(key, val)
        # return path
        return os.path.join(self.filePath, self.fileName)


Index("idx_track_unique_to_eleasemedia", Track.releaseMediaId, Track.trackNumber, unique=True)