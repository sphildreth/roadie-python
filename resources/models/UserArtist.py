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
