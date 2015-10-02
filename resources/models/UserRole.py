from sqlalchemy import Column, String
from sqlalchemy.ext.declarative import declarative_base

from models.ModelBase import ModelBase

Base = declarative_base()


class UserRole(ModelBase):
    __tablename__ = "userRole"

    name = Column(String(80), nullable=False, unique=True)
    description = Column(String(200))

    def __eq__(self, other):
        if not isinstance(other, UserRole):
            return False

        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __unicode__(self):
        return self.name
