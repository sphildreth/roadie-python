from sqlalchemy import Column, ForeignKey, Integer, Boolean, BLOB, String
from sqlalchemy_utils import ScalarListType
from sqlalchemy.orm import relationship

from resources.models.ModelBase import Base
from resources.models.PlaylistTrack import PlaylistTrack


class Playlist(Base):


    isPublic = Column(Boolean(), default=False)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(String(1000))
    thumbnail = Column(BLOB())
    urls = Column(ScalarListType(separator="|"))

    userId = Column(Integer, ForeignKey("user.id"), index=True)
    tracks = relationship(PlaylistTrack, backref="playlist")

    def __unicode__(self):
        return self.user.name + "::" + self.name
