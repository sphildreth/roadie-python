from sqlalchemy import Column, ForeignKey, Integer

from models.ModelBase import ModelBase


class PlaylistTrack(ModelBase):
    __tablename__ = "playlistTrack"

    listNumber = Column(Integer(), nullable=False)
    trackId = Column(Integer(), ForeignKey("track.id"))

    def __unicode__(self):
        return self.track.title
