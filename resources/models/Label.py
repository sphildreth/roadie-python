from sqlalchemy import Column, String, Date
from sqlalchemy_utils import ScalarListType
from sqlalchemy.orm import relationship

from resources.models.ModelBase import Base
from resources.models.ReleaseLabel import ReleaseLabel


class Label(Base):
    name = Column(String(500), nullable=False, index=True, unique=True)
    sortName = Column(String(500))
    musicBrainzId = Column(String(100))
    beginDate = Column(Date())
    endDate = Column(Date())
    imageUrl = Column(String(500))
    tags = Column(ScalarListType(separator="|"))
    alternateNames = Column(ScalarListType(separator="|"), index=True)
    urls = Column(ScalarListType(separator="|"))
    releases = relationship(ReleaseLabel, backref="label")

    def __unicode__(self):
        return self.name

    def info(self):
        return ("Id [" + str(self.id) + "], RoadieId [" + str(self.roadieId) + "], MusicBrainzId [" + str(
            self.musicBrainzId) + "], Name [" + self.name +
                "AlternateNames [" + str(len(self.alternateNames or [])) + "], Tags [" + str(
            len(self.tags or [])) + "]").encode('ascii', 'ignore').decode('utf-8')
