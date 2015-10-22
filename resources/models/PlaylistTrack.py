from sqlalchemy import Column, ForeignKey, Integer

from resources.models.ModelBase import Base


class PlaylistTrack(Base):
    listNumber = Column(Integer, nullable=False)
    trackId = Column(Integer, ForeignKey("track.id"))
    playListId = Column(Integer, ForeignKey("playlist.id"))

    def __unicode__(self):
        return self.playlist.name + " " + self.listNumber + " " + self.track.title
