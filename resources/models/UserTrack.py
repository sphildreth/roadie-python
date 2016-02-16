import arrow
from sqlalchemy import Column, Index, ForeignKey, SmallInteger, Integer, Boolean, DateTime
from resources.models.ModelBase import Base


class UserTrack(Base):
    __table_args__ = (Index('idx_user_track', "userId", "trackId"),)

    isFavorite = Column(Boolean(), default=False)
    isDisliked = Column(Boolean(), default=False)
    rating = Column(SmallInteger(), nullable=False)
    playedCount = Column(Integer, default=0)
    lastPlayed = Column(DateTime(), default=arrow.utcnow().datetime)

    userId = Column(Integer, ForeignKey('user.id'))
    trackId = Column(Integer, ForeignKey('track.id'))

    def __unicode__(self):
        return self.user.name + "::" + self.track.title

    def serialize(self, includes, conn):
        track = None
        if includes and 'track' in includes:
            track = "" if not self.track else self.track.serialize(includes, conn)
        return {
            'id': self.roadieId,
            'createdDate': self.createdDate.isoformat(),
            'isLocked': self.isLocked,
            'lastUpdated': "" if not self.lastUpdated else self.lastUpdated.isoformat(),
            'status': self.status,
            'isFavorite': self.isFavorite,
            'isDisliked': self.isDisliked,
            'rating': self.rating,
            'playedCount': self.playedCount,
            'lastPlayed': "" if not self.lastPlayed else self.lastPlayed.isoformat(),
            'userId': str(self.userId),
            'trackId': str(self.trackId),
            'track': track
        }
