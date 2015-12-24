from sqlalchemy import Column, Enum, ForeignKey, Integer, BLOB, String, Text
from sqlalchemy_utils import ScalarListType
from sqlalchemy.orm import relationship
from resources.models.ModelBase import Base
from resources.models.CollectionRelease import CollectionRelease


class Collection(Base):
    name = Column(String(100), nullable=False, unique=True, index=True)
    edition = Column(String(200))
    # This is the format of the CSV (like number, artist, album)
    listInCSVFormat = Column(String(200))
    # This is the CSV of the list to re-run as albums get added/removed to update list
    listInCSV = Column(Text())
    # This is the number of Releases in the Collection used for Sanity checks and reporting
    collectionCount = Column(Integer)
    collectionType = Column(Enum('Chart', 'Rank', 'Unknown', name='collectionType'), default='Rank')
    description = Column(String(1000))
    thumbnail = Column(BLOB())
    urls = Column(ScalarListType(separator="|"))

    maintainerId = Column(Integer, ForeignKey("user.id"))
    collectionReleases = relationship(CollectionRelease, cascade="all, delete-orphan", backref="collectionReleases")

    def __unicode__(self):
        return self.name
