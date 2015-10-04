from sqlalchemy import Column, String, Date
from sqlalchemy_utils import ScalarListType
from sqlalchemy.orm import relationship

from resources.models.ModelBase import Base
from resources.models.ReleaseLabel import ReleaseLabel


class Label(Base):
    name = Column(String(500), nullable=False, index=True, unique=True)
    sortName = Column(String(500), nullable=False)
    musicBrainzId = Column(String(100))
    beginDate = Column(Date())
    endDate = Column(Date())
    imageUrl = Column(String(500))
    tags = Column(ScalarListType())
    alternateNames = Column(ScalarListType())
    urls = Column(ScalarListType())
    releases = relationship(ReleaseLabel, backref="label")

    def __unicode__(self):
        return self.name

    def info(self):
        return "Id [" + str(self.id) + "], RoadieId [" + str(self.roadieId) + "], MusicBrainzId [" + str(
            self.musicBrainzId) + "], Name [" + self.name + \
               "AlternateNames [" + str(len(self.alternateNames or [])) + "], Tags [" + str(len(self.tags or [])) + "]"
