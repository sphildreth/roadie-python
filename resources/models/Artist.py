from sqlalchemy import Column, ForeignKey, Index, Table, SmallInteger, Integer, BLOB, String, Date, Text, Enum
from sqlalchemy_utils import ScalarListType

from sqlalchemy.orm import relationship

from resources.models.ModelBase import Base
from resources.models.Genre import Genre
from resources.models.Release import Release
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

    name = Column(String(500), nullable=False, index=True, unique=True)
    sortName = Column(String(500))
    # This is calculated when a user rates an artist based on average User Ratings and stored here for performance
    rating = Column(SmallInteger(), nullable=False, default=0)
    # This is a random number generated at generation and then used to select random releases
    random = Column(Integer, nullable=False, default=0, index=True)
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
    alternateNames = Column(ScalarListType(), index=True)
    urls = Column(ScalarListType())
    isniList = Column(ScalarListType())

    releases = relationship(Release, backref="artist")
    images = relationship(Image)
    genres = relationship(Genre, secondary=artistGenreTable, backref="artist")

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
                    if release.labels:
                        for releaseLabel in release.labels:
                            labelNames.append(releaseLabel.label.name + " (" + str(releaseLabel.labelId) + ")")
                    for media in release.media:
                        trackCount = trackCount + len(media.tracks)
                        mediaCount = mediaCount + 1
        return "Id [" + str(self.id) + "], RoadieId [" + str(self.roadieId) + "], MusicBrainzId [" + str(
            self.musicBrainzId) + "], " + \
               "AlternateNames [" + "|".join(self.alternateNames or []) + "], Tags [" + "|".join(self.tags or []) + \
               "], ITunesId [" + str(self.iTunesId) + "], AmgId [" + str(self.amgId) + "], SpotifyId [" + str(
            self.spotifyId) + "], Name [" + str(self.name) + "], SortName [" + str(self.sortName) + \
               "] Releases [" + str(len(self.releases or [])) + "] Labels [" + "|".join(labelNames) + "] Media [" + str(
            mediaCount) + "] Tracks [" + str(trackCount) + "] Images [" + str(
            len(self.images or [])) + "] Genres [" + \
               "|".join(map(lambda x: x.name, self.genres or [])) + "] Associated Artist [" + str(
            len(self.associatedArtists or [])) + "]"

