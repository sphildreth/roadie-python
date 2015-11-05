from sqlalchemy import Column, String
from resources.models.ModelBase import Base


class Genre(Base):
    name = Column(String(100), nullable=False, unique=True, index=True)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name
