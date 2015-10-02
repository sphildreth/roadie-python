import arrow
from sqlalchemy import Column, ForeignKey, Table, Integer, Boolean, BLOB, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from models.ModelBase import ModelBase
from models.UserRole import UserRole

Base = declarative_base()

usersInRolesTable = Table('usersInRoles', Base.metadata,
                          Column('userId', Integer, ForeignKey('user.id')),
                          Column('userRoleId', Integer, ForeignKey('userRole.id')))


class User(ModelBase):
    __tablename__ = "user"

    username = Column(String(20), nullable=False, unique=True, index=True)
    password = Column(String(100), required=True)
    email = Column(String(100), nullable=False, unique=True)
    registeredOn = Column(DateTime(), default=arrow.utcnow().datetime)
    lastLogin = Column(DateTime())
    isActive = Column(Boolean(), default=True)
    avatar = Column(BLOB())
    doUseHtmlPlayer = Column(Boolean(), default=True)
    roles = relationship("UserRole", secondary=usersInRolesTable, backref="user")

    def get_id(self):
        return self.id

    def is_authenticated(self):
        return True

    def is_active(self):
        return self.isActive

    def is_anonymous(self):
        return False

    def has_role(self, role):
        return UserRole(Name=role) in self.roles

    def is_editor(self):
        return UserRole(Name="Admin") in self.roles or UserRole(Name="Editor") in self.roles

    def __repr__(self):
        return '<User %r>' % (self.username)

    def __unicode__(self):
        return self.username
