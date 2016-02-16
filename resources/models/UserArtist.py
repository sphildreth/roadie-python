from sqlalchemy import Column, Index, ForeignKey, SmallInteger, Integer, Boolean
from resources.models.ModelBase import Base


class UserArtist(Base):
    __table_args__ = (Index('idx_user_artist', "userId", "artistId"),)

    isFavorite = Column(Boolean(), default=False)
    isDisliked = Column(Boolean(), default=False)
    rating = Column(SmallInteger(), nullable=False)

    userId = Column(Integer, ForeignKey('user.id'))
    artistId = Column(Integer, ForeignKey("artist.id"))

    def __unicode__(self):
        return self.user.name + "::" + self.artist.name

    def serialize(self, includes, conn):
        artist = None
        if includes and 'artist' in includes:
            artist = "" if not self.artist else self.artist.serialize(includes, conn)
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
            'artistId': str(self.artistId),
            'artist': artist
        }
