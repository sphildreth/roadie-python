from sqlalchemy import Column, Index, ForeignKey, Integer, String, Date
from resources.models.ModelBase import Base


class ReleaseLabel(Base):
    __table_args__ = (Index('idx_release_label', "releaseId", "labelId"),)

    catalogNumber = Column(String(200))
    beginDate = Column(Date())
    endDate = Column(Date())
    releaseId = Column(Integer, ForeignKey('release.id'))
    labelId = Column(Integer, ForeignKey('label.id'))

    def __unicode__(self):
        if not self.label:
            return "---"
        return self.label.name + " (" + self.beginDate.strfttime('%Y') + ")" if self.beginDate else "---"

    def __str__(self):
        if not self.label:
            return "---"
        return self.label.name + " (" + self.beginDate.strfttime('%Y') + ")" if self.beginDate else "---"

    def serialize(self, includes):
        return {
            'id': self.roadieId,
            'beginDate': "" if not self.beginDate else self.beginDate.isoformat(),
            'catalogNumber' : self.catalogNumber,
            'createdDate': self.createdDate.isoformat(),
            'endDate': "" if not self.endDate else self.endDate.isoformat(),
            'isLocked': self.isLocked,
            'lastUpdated': "" if not self.lastUpdated else self.lastUpdated.isoformat(),
            'label': self.label.serialize(includes)
        }