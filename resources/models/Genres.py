from sqlalchemy import Column, String

from models.ModelBase import ModelBase


class Genre(ModelBase):
    __tablename__ = "genre"

    name = Column(String(100), required=True, unique=True)

    def __unicode__(self):
        return self.name
