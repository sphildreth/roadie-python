import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, SmallInteger, String, Date, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
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
    artistType = Column(Enum('person', 'group', 'orchestra', 'choir', 'character', 'other', name='artistType'))
    imageUrl = Column(String(500), nullable=True)
    bioContext = Column(Text(), nullable=True)
    tags = relationship('ArtistTagsSearchResult', backref="artistReference")
    alternateNames =  relationship('ArtistAlternateNamesSearchResult', backref="artistReference")
    urls = relationship('ArtistUrlsSearchResult', backref="artistReference")
    isniList = relationship('ArtistIsniSearchResult', backref="artistReference")
    releases = relationship('ArtistReleaseSearchResult', backref="artistReference")

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return "Id [" + str(self.id) + "], RoadieId [" + str(self.roadieId) + "], MusicBrainzId [" + str(self.musicBrainzId) + "], " + \
               "AlternateNames [" + str(len(self.alternateNames or [])) + "], Tags [" + str(len(self.tags or [])) + \
               "], ITunesId [" + str(self.iTunesId) + "], AmgId [" + str(self.amgId) + "], SpotifyId [" + str(self.spotifyId) + "], Name [" + str(self.name) + "], SortName [" + str(self.sortName) + "]"


class ArtistTagsSearchResult(Base):

    __tablename__ = "artistTagsReference"

    id = Column(Integer, primary_key=True)
    tag = Column(String(100), nullable=False, unique=True)
    artistId = Column(Integer(), ForeignKey('artistReference.id'))


class ArtistAlternateNamesSearchResult(Base):

    __tablename__ = "artistAlternateNamesReference"

    id = Column(Integer, primary_key=True)
    name = Column(String(500), nullable=False, unique=True)
    artistId = Column(Integer(), ForeignKey('artistReference.id'))


class ArtistUrlsSearchResult(Base):

    __tablename__ = "artistUrlsReference"

    id = Column(Integer, primary_key=True)
    url = Column(String(500), nullable=False)
    artistId = Column(Integer(), ForeignKey('artistReference.id'))


class ArtistIsniSearchResult(Base):

    __tablename__ = "artistIsniReference"

    id = Column(Integer, primary_key=True)
    isni = Column(String(100), nullable=False, unique=True)
    artistId = Column(Integer(), ForeignKey('artistReference.id'))


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
    tags = relationship('ArtistReleaseTagsSearchResult', backref="releaseReference")
    urls = relationship('ArtistReleaseUrlsSearchResult', backref="releaseReference")
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



class ArtistReleaseTagsSearchResult(Base):

    __tablename__ = "artistReleaseTagsReference"

    id = Column(Integer, primary_key=True)
    tag = Column(String(100), nullable=False, unique=True)
    releaseId = Column(Integer(), ForeignKey('releaseReference.id'))


class ArtistReleaseUrlsSearchResult(Base):

    __tablename__ = "artistReleaseUrlsReference"

    id = Column(Integer, primary_key=True)
    url = Column(String(500), nullable=False)
    releaseId = Column(Integer(), ForeignKey('releaseReference.id'))



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
    tags = relationship('ArtistReleaseLabellTagsSearchResult', backref="labelReference")
    alternateNames =  relationship('ArtistReleaseLabelAlterrnateNamesSearchResult', backref="labelReference")
    urls = relationship('ArtistReleaseLabelUrlsSearchResult', backref="labelReference")


    def __init__(self, name):
        self.name = name


    def __str__(self):
        return "Id [" + str(self.id) + "], RoadieId [" + str(self.roadieId) + "], MusicBrainzId [" + str(self.musicBrainzId) + "], Name [" + self.name + \
       "AlternateNames [" + str(len(self.alternateNames or [])) + "], Tags [" + str(len(self.tags or [])) + "]"


class ArtistReleaseLabellTagsSearchResult(Base):

    __tablename__ = "artistReleaseLabelTagsReference"

    id = Column(Integer, primary_key=True)
    tag = Column(String(100), nullable=False, unique=True)
    labelId = Column(Integer(), ForeignKey('labelReference.id'))


class ArtistReleaseLabelAlterrnateNamesSearchResult(Base):

    __tablename__ = "artistReleaseLabelAlternateNamesReference"

    id = Column(Integer, primary_key=True)
    name = Column(String(500), nullable=False, unique=True)
    labelId = Column(Integer(), ForeignKey('labelReference.id'))


class ArtistReleaseLabelUrlsSearchResult(Base):

    __tablename__ = "artistReleaseLabelUrlsReference"

    id = Column(Integer, primary_key=True)
    url = Column(String(500), nullable=False)
    labelId = Column(Integer(), ForeignKey('labelReference.id'))




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