from sqlalchemy import Column, String, Date
from sqlalchemy_utils import ScalarListType
from sqlalchemy.orm import relationship

from models.ModelBase import ModelBase


class Label(ModelBase):
    __tablename__ = "label"

    name = Column(String(500), nullable=False, index=True)
    sortName = Column(String(500), nullable=False)
    musicBrainzId = Column(String(100))
    beginDate = Column(Date())
    endDate = Column(Date())
    imageUrl = Column(String(500))
    tags = Column(ScalarListType())
    alternateNames = Column(ScalarListType())
    urls = Column(ScalarListType())
    releases = relationship("Release", backref="label")

    def __init__(self, name):
        self.name = name

    def __unicode__(self):
        return self.name

    def info(self):
        return "Id [" + str(self.id) + "], RoadieId [" + str(self.roadieId) + "], MusicBrainzId [" + str(
            self.musicBrainzId) + "], Name [" + self.name + \
               "AlternateNames [" + str(len(self.alternateNames or [])) + "], Tags [" + str(len(self.tags or [])) + "]"
