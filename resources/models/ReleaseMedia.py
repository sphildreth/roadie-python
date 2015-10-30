from sqlalchemy import Column, ForeignKey, Integer, SmallInteger, String
from sqlalchemy.orm import relationship

from resources.models.ModelBase import Base
from resources.models.Track import Track


class ReleaseMedia(Base):

    # The cd number ie cd x of x
    releaseMediaNumber = Column(SmallInteger(), default=0)
    # Any potential subtitle of cd x of x; see 'Star Time' from James Brown
    releaseSubTitle = Column(String(500))
    # Number of Tracks that should be on the Release Media
    trackCount = Column(SmallInteger(), nullable=False)
    # Tracks For The Release Media
    tracks = relationship(Track, cascade="all, delete-orphan", backref="releasemedia")
    # The Release for the Release Media
    releaseId = Column(Integer, ForeignKey("release.id"), index=True)

    def info(self):
        return ( "Id [" + str(self.id) + "], RoadieId [" + str(self.roadieId) +
                "], ReleaseMediaNumber [" + str(self.releaseMediaNumber) +
               "], ReleaseSubTitle [" + str(self.releaseSubTitle) + "], trackCount [" + str(self.trackCount) +
               "]").encode('ascii', 'ignore').decode('utf-8')

    def __unicode__(self):
        return self.release.title + " " + self.releaseMediaNumber

    def __str__(self):
        return self.release.title + " " + str(self.releaseMediaNumber)
