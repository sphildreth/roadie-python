from sqlalchemy import Column, ForeignKey, Integer, BLOB, String

from models.ModelBase import ModelBase


class Image(ModelBase):
    __tablename__ = "image"

    # If this is used then the image is stored in the database
    image = Column(BLOB, nullable=False)
    # If this is used then the image is remote and this is the url
    url = Column(String(500))
    caption = Column(String(100))

    artistId = Column(Integer(), ForeignKey("artist.id"))
    releaseId = Column(Integer(), ForeignKey("release.id"))

    def __unicode__(self):
        return self.caption
