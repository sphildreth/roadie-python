from sqlalchemy import Column, ForeignKey, Integer, BLOB, String, Text
from sqlalchemy_utils import ScalarListType
from sqlalchemy.orm import relationship

from models.ModelBase import ModelBase


class Collection(ModelBase):
    __tablename__ = "collection"

    name = Column(String(100), nullable=False, unique=True, index=True)
    edition = Column(String(200))
    # This is the format of the CSV (like number, artist, album)
    listInCSVFormat = Column(String(200))
    # This is the CSV of the list to re-run as albums get added/removed to update list
    listInCSV = Column(Text())
    description = Column(String(1000))
    thumbnail = Column(BLOB())
    urls = Column(ScalarListType())

    maintainerId = Column(Integer(), ForeignKey("user.id"))
    releases = relationship("CollectionRelease", backref="release")

    def __unicode__(self):
        return self.name
