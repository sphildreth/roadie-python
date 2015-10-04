from sqlalchemy import Column, ForeignKey, Integer, String, Date

from resources.models.ModelBase import Base


class ReleaseLabel(Base):


    catalogNumber = Column(String(200))
    beginDate = Column(Date())
    endDate = Column(Date())
    releaseId = Column(Integer, ForeignKey('release.id'))
    labelId = Column(Integer, ForeignKey('label.id'))

    def __unicode__(self):
        return self.label.name + " (" + self.beginDate.strfttime('%Y') + ")"
