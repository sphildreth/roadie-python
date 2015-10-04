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
        if self.releases:
            for release in self.releases:
                if release.media:
                    for media in release.media:
                        trackCount = trackCount + len(media.tracks)
        return "Id [" + str(self.id) + "], RoadieId [" + str(self.roadieId) + "], MusicBrainzId [" + str(
            self.musicBrainzId) + "], " + \
               "AlternateNames [" + "|".join(self.alternateNames or []) + "], Tags [" + "|".join(self.tags or []) + \
               "], ITunesId [" + str(self.iTunesId) + "], AmgId [" + str(self.amgId) + "], SpotifyId [" + str(
            self.spotifyId) + "], Name [" + str(self.name) + "], SortName [" + str(self.sortName) + \
               "] Releases [" + str(len(self.releases or [])) + "] Tracks [" + str(trackCount) + "] Images [" + str(
            len(self.images or [])) + "] Genres [" + \
               "|".join(map(lambda x: x.name, self.genres or [])) + "] Associated Artist [" + str(
            len(self.associatedArtists or [])) + "]"

    def mergeWithArtist(self, right):
        """

        :type right: Artist
        """
        result = self
        if not right:
            return result
        if not result.name and right.name:
            result.name = right.name
        elif right.name and result.name.lower().strip() != right.name.lower().strip():
            if not result.alternateNames:
                result.alternateNames = []
            if not right.name in result.alternateNames:
                result.alternateNames.append(right.name)
        if not result.sortName and right.sortName:
            result.sortName = right.sortName
        elif right.sortName and result.sortName.lower().strip() != right.sortName.lower().strip():
            if not result.alternateNames:
                result.alternateNames = []
            if not right.sortName in result.alternateNames:
                result.alternateNames.append(right.sortName)
        result.musicBrainzId = result.musicBrainzId or right.musicBrainzId
        result.iTunesId = result.iTunesId or right.iTunesId
        result.amgId = result.amgId or right.amgId
        result.spotifyId = result.spotifyId or right.spotifyId
        result.birthDate = result.birthDate or right.birthDate
        result.beginDate = result.beginDate or right.beginDate
        result.endDate = result.endDate or right.endDate
        if not result.artistType or result.artistType.lower().strip() == "unknown" and right.artistType:
            result.artistType = right.artistType
        if not result.images and right.images:
            result.images = right.images
        elif result.images and right.images:
            for image in right.images:
                if not image in result.images:
                    result.images.append(image)
        result.bioContext = result.bioContext or right.bioContext
        if not result.tags and right.tags:
            result.tags = right.tags
        elif result.tags and right.tags:
            for tag in right.tags:
                if not tag in result.tags:
                    result.tags.append(tag)
        if not result.alternateNames and right.alternateNames:
            result.alternateNames = right.alternateNames
        elif result.alternateNames and right.alternateNames:
            for alternateName in right.alternateNames:
                if not alternateName in result.alternateNames:
                    result.alternateNames.append(alternateName)
        if not result.urls and right.urls:
            result.urls = right.urls
        elif result.urls and right.urls:
            for url in right.urls:
                if not url in result.urls:
                    result.urls.append(url)
        if not result.isniList and right.isniList:
            result.isniList = right.isniList
        elif result.isniList and right.isniList:
            for isni in right.isniList:
                if not isni in result.isniList:
                    result.isniList.append(isni)
        if not result.releases and right.releases:
            result.releases = right.releases
        elif result.releases and right.releases:
            for release in right.releases:
                if not filter(lambda x: x.title == release.title, result.releases):
                    result.releases.append(release)
        if not result.genres and right.genres:
            result.genres = right.genres
        elif result.genres and right.genres:
            for genre in right.genres:
                if not genre in result.genres:
                    result.genres.append(genre)
        return result
