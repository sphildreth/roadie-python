from sqlalchemy import Column, String, Date
from sqlalchemy_utils import ScalarListType
from sqlalchemy.orm import relationship
from resources.models.ModelBase import Base
from resources.models.ReleaseLabel import ReleaseLabel


class Label(Base):
    name = Column(String(250), nullable=False, index=True, unique=True)
    sortName = Column(String(500))
    musicBrainzId = Column(String(100))
    beginDate = Column(Date())
    endDate = Column(Date())
    imageUrl = Column(String(500))
    tags = Column(ScalarListType(separator="|"))
    alternateNames = Column(ScalarListType(separator="|"))
    urls = Column(ScalarListType(separator="|"))
    releases = relationship(ReleaseLabel, backref="label")

    def __unicode__(self):
        return self.name

    def info(self):
        return ("Id [" + str(self.id) + "], RoadieId [" + str(self.roadieId) + "], MusicBrainzId [" + str(
            self.musicBrainzId) + "], Name [" + self.name +
                "AlternateNames [" + str(len(self.alternateNames or [])) + "], Tags [" + str(
            len(self.tags or [])) + "]").encode('ascii', 'ignore').decode('utf-8')

    def __repr__(self):
        return self.name

    def serialize(self, includes):
        return {
            'id': self.roadieId,
            'alternateNames': "" if not self.alternateNames else '|'.join(self.alternateNames),
            'beginDate': "" if not self.beginDate else self.beginDate.isoformat(),
            'createdDate': self.createdDate.isoformat(),
            'endDate': "" if not self.endDate else self.endDate.isoformat(),
            'imageUrl': self.imageUrl,
            'lastUpdated': "" if not self.lastUpdated else self.lastUpdated.isoformat(),
            'musicBrainzId': self.musicBrainzId,
            'name': self.name,
            'sortName': self.sortName,
            'tags': "" if not self.tags else '|'.join(self.tags),
            'urls': "" if not self.urls else '|'.join(self.urls)
        }