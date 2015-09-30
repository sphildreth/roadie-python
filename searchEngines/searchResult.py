import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, SmallInteger, String, Date, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils import ScalarListType
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class ArtistSearchResult(Base):

    __tablename__ = "artistReference"

    id = Column(Integer, primary_key=True)
    roadieId = Column(String(100), nullable=True)
    name = Column(String(500), nullable=False, index=True,unique=True)
    sortName = Column(String(500), nullable=False)
    musicBrainzId = Column(String(100), nullable=True)
    iTunesId = Column(String(100), nullable=True)
    amgId = Column(String(100), nullable=True)
    spotifyId = Column(String(100), nullable=True)
    beginDate = Column(Date(), nullable=True)
    endDate = Column(Date(), nullable=True)
    artistType = Column(Enum('Person', 'Group', 'Orchestra', 'Choir', 'Character', 'Other', name='artistType'))
    imageUrl = Column(String(500), nullable=True)
    bioContext = Column(Text(), nullable=True)
    tags = Column(ScalarListType(), nullable=True)
    alternateNames =  Column(ScalarListType(), nullable=True)
    urls = Column(ScalarListType(), nullable=True)
    isniList = Column(ScalarListType(), nullable=True)
    releases = relationship('ArtistReleaseSearchResult', backref="artistReference")

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return "Id [" + str(self.id) + "], RoadieId [" + str(self.roadieId) + "], MusicBrainzId [" + str(self.musicBrainzId) + "], " + \
               "AlternateNames [" + str(len(self.alternateNames or [])) + "], Tags [" + str(len(self.tags or [])) + \
               "], ITunesId [" + str(self.iTunesId) + "], AmgId [" + str(self.amgId) + "], SpotifyId [" + str(self.spotifyId) + "], Name [" + str(self.name) + "], SortName [" + str(self.sortName) + "]"


class ArtistReleaseSearchResult(Base):

    __tablename__ = "releaseReference"

    id = Column(Integer, primary_key=True)
    roadieId = Column(String(100), nullable=True)
    title = Column(String(500), nullable=False, index=True)
    releaseDate = Column(Date(), nullable=True)
    trackCount = Column(SmallInteger(), nullable=False)
    coverUrl = Column(String(500), nullable=True)
    iTunesId = Column(String(100), nullable=True)
    lastFMId = Column(String(100), nullable=True)
    musicBrainzId = Column(String(100), nullable=True)
    spotifyId = Column(String(100), nullable=True)
   # labels = relationship('ArtistReleaseLabelSearchResult', backref="releaseReference")
    tags = Column(ScalarListType(), nullable=True)
    urls = Column(ScalarListType(), nullable=True)
    tracks = relationship('ArtistReleaseTrackSearchResult', backref="releaseReference")
    artistId = Column(Integer(), ForeignKey('artistReference.id'))

    def __init__(self, title, releaseDate, trackCount, coverUrl):
        self.title = title
        self.releaseDate = releaseDate
        self.trackCount = trackCount
        self.coverUrl = coverUrl

    def __str__(self):
       return "Id [" + str(self.id) + "], RoadieId [" + str(self.roadieId) + "], MusicBrainzId [" + str(self.musicBrainzId) + "], ITunesId [" + str(self.iTunesId) + \
              "], LastFMId [" + str(self.lastFMId) + "], ReleaseDate [" + str(self.releaseDate) + "], TrackCount [" + str(self.trackCount) + "], Title [" + str(self.title) + "]"


class ArtistReleaseLabelSearchResult(Base):

    __tablename__ = "labelReference"

    id = Column(Integer, primary_key=True)
    roadieId = Column(String(100), nullable=True)
    name = Column(String(500), nullable=False, index=True)
    sortName = Column(String(500), nullable=False)
    musicBrainzId = Column(String(100), nullable=True)
    beginDate = Column(Date(), nullable=True)
    endDate = Column(Date(), nullable=True)
    imageUrl = Column(String(500), nullable=True)
    tags = Column(ScalarListType(), nullable=True)
    alternateNames = Column(ScalarListType(), nullable=True)
    urls = Column(ScalarListType(), nullable=True)


    def __init__(self, name):
        self.name = name


    def __str__(self):
        return "Id [" + str(self.id) + "], RoadieId [" + str(self.roadieId) + "], MusicBrainzId [" + str(self.musicBrainzId) + "], Name [" + self.name + \
       "AlternateNames [" + str(len(self.alternateNames or [])) + "], Tags [" + str(len(self.tags or [])) + "]"



class ArtistReleaseTrackSearchResult(Base):

    __tablename__ = "trackReference"

    id = Column(Integer, primary_key=True)
    roadieId = Column(String(100), nullable=True)
    musicBrainzId = Column(String(100), nullable=True)
    spotifyId = Column(String(100), nullable=True)
    title= Column(String(250), nullable=False)
    releaseMediaNumber = Column(SmallInteger(), nullable=False)
    trackNumber = Column(SmallInteger(), nullable=False)
    duration = Column(Integer(), nullable=True)
    releaseId = Column(Integer(), ForeignKey('releaseReference.id'))

    def __init__(self, title):
        self.title = title


    def __str__(self):
        return "Id [" + str(self.id) +"], RoadieId [" + str(self.roadieId) + "], MusicBrainzId [" + str(self.musicBrainzId) \
               + "], Title [" + str(self.title) + "], ReleaseMediaNumber[" + str(self.releaseMediaNumber) + "], TrackNumber [" + str(self.trackNumber) \
               + "], Duration [" + str(self.duration) + "]"



#engine = create_engine("sqlite:///artistsSearchReference.db")
#Base.metadata.create_all(engine)