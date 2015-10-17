from sqlalchemy import Column, ForeignKey, Integer, BLOB, String

from resources.models.ModelBase import Base


class Image(Base):

    # If this is used then the image is stored in the database
    image = Column(BLOB, nullable=False)
    # If this is used then the image is remote and this is the url
    url = Column(String(500))
    caption = Column(String(100))

    artistId = Column(Integer, ForeignKey("artist.id"), index=True)
    releaseId = Column(Integer, ForeignKey("release.id"), index=True)

    def __unicode__(self):
        return self.caption
