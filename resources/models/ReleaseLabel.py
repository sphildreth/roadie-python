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
        return self.label.name + " (" + self.beginDate.strfttime('%Y') + ")"
