from sqlalchemy import Column, ForeignKey, Table, SmallInteger, Integer, BLOB, String, Date, Text, Enum
from sqlalchemy_utils import ScalarListType
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from models.ModelBase import ModelBase

Base = declarative_base()

artistAssociationTable = Table('artistAssociation', Base.metadata,
                               Column('artistId', Integer, ForeignKey('artist.id')),
                               Column('associatedArtistId', Integer, ForeignKey('artist.id')))


class Artist(ModelBase):
    __tablename__ = "artist"

    associatedArtists = relationship("Artist", secondary=artistAssociationTable)
    name = Column(String(500), nullable=False, index=True, unique=True)
    sortName = Column(String(500), nullable=False)
    # This is calculated when a user rates an artist based on average User Ratings and stored here for performance
    rating = Column(SmallInteger(), nullable=False)
    # This is a random number generated at generation and then used to select random releases
    random = Column(Integer(), nullable=False)
    realName = Column(String(500))
    musicBrainzId = Column(String(100))
    iTunesId = Column(String(100))
    amgId = Column(String(100))
    spotifyId = Column(String(100))
    thumbnail = Column(BLOB())
    profile = Column(String(2000))
    birthDate = Column(Date())
    beginDate = Column(Date())
    endDate = Column(Date())
    artistType = Column(Enum('Person', 'Group', 'Orchestra', 'Choir', 'Character', 'Other', name='artistType'))
    bioContext = Column(Text())
    tags = Column(ScalarListType())
    alternateNames = Column(ScalarListType())
    urls = Column(ScalarListType())
    isniList = Column(ScalarListType())

    releases = relationship('Release', backref="artist")
    images = relationship("Image")

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    def info(self):
        return "Id [" + str(self.id) + "], RoadieId [" + str(self.roadieId) + "], MusicBrainzId [" + str(
            self.musicBrainzId) + "], " + \
               "AlternateNames [" + str(len(self.alternateNames or [])) + "], Tags [" + str(len(self.tags or [])) + \
               "], ITunesId [" + str(self.iTunesId) + "], AmgId [" + str(self.amgId) + "], SpotifyId [" + str(
            self.spotifyId) + "], Name [" + str(self.name) + "], SortName [" + str(self.sortName) + "]"
