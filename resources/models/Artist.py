from sqlalchemy import Column, ForeignKey, Index, Table, SmallInteger, Integer, BLOB, String, Date, Text, Enum
from sqlalchemy_utils import ScalarListType
from sqlalchemy.orm import relationship
from resources.models.ModelBase import Base
from resources.models.Genre import Genre
from resources.models.Release import Release
from resources.models.UserArtist import UserArtist
from resources.models.Image import Image

artistAssociationTable = Table('artistAssociation', Base.metadata,
                               Column('artistId', Integer, ForeignKey('artist.id'), primary_key=True),
                               Column('associatedArtistId', Integer, ForeignKey('artist.id'), primary_key=True))

artistGenreTable = Table('artistGenreTable', Base.metadata,
                         Column('artistId', Integer, ForeignKey('artist.id'), index=True),
                         Column('genreId', Integer, ForeignKey('genre.id')))

Index("idx_artistAssociation", artistAssociationTable.c.artistId, artistAssociationTable.c.associatedArtistId)
Index("idx_artistGenreAssociation", artistGenreTable.c.artistId, artistGenreTable.c.genreId)


class Artist(Base):
    # For artists with same name append ' (XXXX)' as year started to make unique
    # Example: 'Prism (1974)', 'Prism (1977)', 'Prism (2013)'
    name = Column(String(250), nullable=False, index=True, unique=True)
    sortName = Column(String(250), unique=True)
    # This is calculated when a user rates an artist based on average User Ratings and stored here for performance
    rating = Column(SmallInteger(), nullable=False, default=0)
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
    tags = Column(ScalarListType(separator="|"))
    alternateNames = Column(ScalarListType(separator="|"))
    urls = Column(ScalarListType(separator="|"))
    isniList = Column(ScalarListType(separator="|"))

    releases = relationship(Release, cascade="all, delete-orphan", backref="artist")
    images = relationship(Image, cascade="all, delete-orphan", backref="artist")
    genres = relationship(Genre, secondary=artistGenreTable, backref="artist")

    userRatings = relationship(UserArtist, cascade="all, delete-orphan", backref="artist")

    associated_artists = relationship("Artist",
                                      secondary="artistAssociation",
                                      primaryjoin="Artist.id==artistAssociation.c.artistId",
                                      secondaryjoin="Artist.id==artistAssociation.c.associatedArtistId",
                                      backref="associatedArtists")

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    def info(self):
        trackCount = 0
        mediaCount = 0
        labelNames = []
        if self.releases:
            for release in self.releases:
                if release.media:
                    if release.releaseLabels:
                        for releaseLabel in release.releaseLabels:
                            labelNames.append(releaseLabel.label.name + " (" + str(releaseLabel.labelId) + ")")
                    for media in release.media:
                        trackCount += len(media.tracks)
                        mediaCount += 1
        return ("Id [" + str(self.id) + "], RoadieId [" + str(self.roadieId) + "], MusicBrainzId [" + str(
            self.musicBrainzId) + "], " +
                "AlternateNames [" + "|".join(self.alternateNames or []) + "], Tags [" + "|".join(self.tags or []) +
                "], ITunesId [" + str(self.iTunesId) + "], AmgId [" + str(self.amgId) + "], SpotifyId [" + str(
            self.spotifyId) + "], Name [" + str(self.name) + "], SortName [" + str(self.sortName) +
                "] Releases [" + str(len(self.releases or [])) + "] Labels [" + "|".join(
            labelNames) + "] Media [" + str(
            mediaCount) + "] Tracks [" + str(trackCount) + "] Images [" + str(
            len(self.images or [])) + "] Genres [" +
                "|".join(map(lambda x: x.name, self.genres or [])) + "] Associated Artist [" + str(
            len(self.associatedArtists or [])) + "]").encode('ascii', 'ignore').decode('utf-8')
