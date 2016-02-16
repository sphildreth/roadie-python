from sqlalchemy import Column, Index, ForeignKey, SmallInteger, Integer, Boolean
from resources.models.ModelBase import Base


class UserRelease(Base):
    __table_args__ = (Index('idx_user_release', "userId", "releaseId"),)

    isFavorite = Column(Boolean(), default=False)
    isDisliked = Column(Boolean(), default=False)
    rating = Column(SmallInteger(), nullable=False)

    userId = Column(Integer, ForeignKey('user.id'))
    releaseId = Column(Integer, ForeignKey("release.id"))

    def __unicode__(self):
        return self.user.name + "::" + self.release.title

    def serialize(self, includes, conn):
        release = None
        if includes and 'artist' in includes:
            release = "" if not self.release else self.release.serialize(includes, conn)
        return {
            'id': self.roadieId,
            'createdDate': self.createdDate.isoformat(),
            'isLocked': self.isLocked,
            'lastUpdated': "" if not self.lastUpdated else self.lastUpdated.isoformat(),
            'status': self.status,
            'isFavorite': self.isFavorite,
            'isDisliked': self.isDisliked,
            'rating': self.rating,
            'userId': str(self.userId),
            'releaseId': str(self.releaseId),
            'release': release
        }