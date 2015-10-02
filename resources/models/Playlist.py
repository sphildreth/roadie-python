from sqlalchemy import Column, ForeignKey, Integer, Boolean, BLOB, String
from sqlalchemy_utils import ScalarListType
from sqlalchemy.orm import relationship

from models.ModelBase import ModelBase


class Playlist(ModelBase):
    __tablename__ = "playlist"

    isPublic = Column(Boolean(), default=False)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(String(1000))
    thumbnail = Column(BLOB())
    urls = Column(ScalarListType())

    userId = Column(Integer(), ForeignKey("user.id"), index=True)
    tracks = relationship("PlaylistTrack", backref="track")

    def __unicode__(self):
        return self.user.name + "::" + self.name
