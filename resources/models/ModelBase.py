import arrow
from sqlalchemy import Column, Integer, Boolean, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ModelBase(Base):
    id = Column(Integer, primary_key=True)
    isLocked = Column(Boolean(), default=False)
    roadieId = Column(String(36), nullable=True)
    createdDate = Column(DateTime(), default=arrow.utcnow().datetime)
    lastUpdated = Column(DateTime(), nullable=True)
