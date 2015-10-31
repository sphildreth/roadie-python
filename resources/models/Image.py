from sqlalchemy import Column, ForeignKey, LargeBinary, Index, Integer, String
from resources.models.ModelBase import Base


class Image(Base):

    # If this is used then the image is stored in the database
    image = Column(LargeBinary(length=16777215), default=None)
    # If this is used then the image is remote and this is the url
    url = Column(String(500))
    caption = Column(String(100))
    # This is a PhotoHash of the image for assistance in deduping
    signature = Column(String(50))

    artistId = Column(Integer, ForeignKey("artist.id"), index=True)
    releaseId = Column(Integer, ForeignKey("release.id"), index=True)

    def __unicode__(self):
        return self.caption

    def __str__(self):
        return self.caption or self.signature
