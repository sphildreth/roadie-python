import arrow
from sqlalchemy import Column, ForeignKey, Table, Integer, Boolean, BLOB, String, DateTime
from sqlalchemy.orm import relationship
from resources.models.ModelBase import Base
from resources.models.Collection import Collection
from resources.models.Playlist import Playlist
from resources.models.UserArtist import UserArtist
from resources.models.UserRelease import UserRelease
from resources.models.UserRole import UserRole
from resources.models.UserTrack import UserTrack

usersInRolesTable = Table('usersInRoles', Base.metadata,
                          Column('userId', Integer, ForeignKey('user.id'), index=True),
                          Column('userRoleId', Integer, ForeignKey('userrole.id')))


class User(Base):
    username = Column(String(20), nullable=False, unique=True, index=True)
    password = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    timezone = Column(String(50))
    registeredOn = Column(DateTime(), default=arrow.utcnow().datetime)
    lastLogin = Column(DateTime())
    isActive = Column(Boolean(), default=True)
    avatar = Column(BLOB())
    doUseHtmlPlayer = Column(Boolean(), default=True)
    roles = relationship(UserRole, secondary=usersInRolesTable, backref="user")

    collectionMaintainer = relationship(Collection, backref="user")
    playlistUser = relationship(Playlist, backref="user")

    artists = relationship(UserArtist, cascade="all, delete-orphan", backref="user")
    releases = relationship(UserRelease, cascade="all, delete-orphan", backref="user")
    tracks = relationship(UserTrack, cascade="all, delete-orphan", backref="user")

    def get_id(self):
        return self.roadieId

    def is_authenticated(self):
        return True

    def is_active(self):
        return self.isActive

    def is_anonymous(self):
        return False

    def has_role(self, role):
        return UserRole(name=role) in self.roles

    def is_editor(self):
        return UserRole(name="Admin") in self.roles or UserRole(name="Editor") in self.roles

    def __repr__(self):
        return self.username

    def __unicode__(self):
        return self.username
