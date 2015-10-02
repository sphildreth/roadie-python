from sqlalchemy import Column, ForeignKey, Integer

from models.ModelBase import ModelBase


class CollectionRelease(ModelBase):
    __tablename__ = "collectionRelease"

    listNumber = Column(Integer(), nullable=False)
    releaseId = Column(Integer(), ForeignKey("release.id"))

    def __unicode__(self):
        return self.release.title
