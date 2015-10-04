from sqlalchemy import Column, String

from resources.models.ModelBase import Base


class Genre(Base):
    name = Column(String(100), nullable=False, unique=True)

    def __unicode__(self):
        return self.name
