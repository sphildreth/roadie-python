from sqlalchemy import Column, Index, ForeignKey, SmallInteger, Integer, Boolean

from models.ModelBase import ModelBase


class UserRelease(ModelBase):
    __tablename__ = "userRelease"

    __table_args__ = (Index('idx_user_release', "userId", "releaseId"))

    isFavorite = Column(Boolean(), default=False)
    isDisliked = Column(Boolean(), default=False)
    rating = Column(SmallInteger(), nullable=False)

    userId = Column(Integer(), ForeignKey('user.id'))
    releaseId = Column(Integer(), ForeignKey("release.id"))

    def __unicode__(self):
        return self.user.name + "::" + self.release.title
