from sqlalchemy import Column, ForeignKey, Index, Integer
from resources.models.ModelBase import Base


class CollectionRelease(Base):
    __table_args__ = (Index('idx_collection_release', "collectionId", "releaseId"),)

    listNumber = Column(Integer, nullable=False)
    releaseId = Column(Integer, ForeignKey("release.id"))
    collectionId = Column(Integer, ForeignKey('collection.id'))

    def __unicode__(self):
        return self.release.title
