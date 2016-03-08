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
    # https://en.wikipedia.org/wiki/International_Standard_Recording_Code
    isrc = Column(String(15), unique=True)
    alternateNames = Column(ScalarListType(separator="|"))
    trackNumber = Column(SmallInteger(), nullable=False)
    # Seconds long
    duration = Column(Integer)
    tags = Column(ScalarListType(separator="|"))

    # This is the TPE1 ("Artist") if different than TPE2 ("Album Artist")
    # An example would be TPE2 of "Titanic: Music from the Motion Picture" and TPE1 of "Celine Dion" for Track #14
    artistId = Column(Integer, ForeignKey("artist.id"))

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

    def info(self, includePathInfo=False):
        fileAndNameInfo = "FilePath [" + str(self.filePath) + "], " + \
                          "FileName [" + str(self.fileName) + "], "
        if not includePathInfo:
            fileAndNameInfo = ""
        return ("Id [" + str(self.id) + "], " +
                "RoadieId [" + str(self.roadieId) + "], " +
                "Hash [" + str(self.hash) + "], " +
                "Title [" + str(self.title) + "], " +
                "TrackNumber [" + str(self.trackNumber) + "], " +
                fileAndNameInfo +
                "Duration [" + str(self.duration) + "]").encode('ascii', 'ignore').decode('utf-8')

    def fullPath(self):
        if not self.filePath or not self.fileName:
            return None
        return os.path.join(self.filePath, self.fileName)

    def serialize(self, includes, conn):
        trackArtist = None
        trackRelease = None
        trackReleaseMedia = None
        if includes and 'releaseMedia' in includes:
            trackReleaseMedia = self.releasemedia.serialize(None, conn)
        if includes and 'artist' in includes:
            if self.artistId:
                trackArtist = self.artist.serialize(None, conn)
            else:
                trackArtist = self.releasemedia.release.artist.serialize(None, conn)
        if includes and 'release' in includes:
            trackRelease = self.releasemedia.release.serialize(None, conn)
        return {
            'id': self.roadieId,
            'alternateNames': "" if not self.alternateNames else '|'.join(self.alternateNames),
            'amgId': self.amgId,
            'artistId': self.artist.roadieId if self.artist else self.releasemedia.release.artist.roadieId,
            'createdDate': self.createdDate.isoformat(),
            'duration': self.duration,
            'fileSize': self.fileSize,
            'hash': self.hash,
            'isLocked': self.isLocked,
            'isrc': self.isrc,
            'isValid': True if self.hash else False,
            'lastPlayed': "" if not self.lastPlayed else self.lastPlayed.isoformat(),
            'lastUpdated': "" if not self.lastUpdated else self.lastUpdated.isoformat(),
            'mediaId': self.releasemedia.roadieId,
            'musicBrainzId': self.musicBrainzId,
            'partTitles': "" if not self.partTitles else '|'.join(self.partTitles),
            'playedCount': self.playedCount,
            'rating': self.rating,
            'releaseId': self.releasemedia.release.roadieId,
            'spotifyId': self.spotifyId,
            'status': self.status,
            'tags': "" if not self.tags else '|'.join(self.tags),
            'title': self.title,
            'trackNumber': self.trackNumber,
            'releaseMedia': trackReleaseMedia,
            'release': trackRelease,
            'artist': trackArtist
        }


Index("idx_track_unique_to_eleasemedia", Track.releaseMediaId, Track.trackNumber, unique=True)
