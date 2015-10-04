import arrow
from sqlalchemy import Column, Integer, Boolean, String, SmallInteger, DateTime
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.declarative import declarative_base


class ModelBase(object):
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True)
    isLocked = Column(Boolean(), default=False)
    status = Column(SmallInteger(), default=0)
    roadieId = Column(String(36), nullable=True)
    createdDate = Column(DateTime(), default=arrow.utcnow().datetime)
    lastUpdated = Column(DateTime(), nullable=True)


Base = declarative_base(cls=ModelBase)
