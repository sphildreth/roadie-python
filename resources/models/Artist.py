import base64

from resources.common import *

from sqlalchemy import Column, ForeignKey, Index, Table, SmallInteger, Integer, BLOB, String, Date, Text, Enum
from sqlalchemy_utils import ScalarListType
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text
from resources.models.ModelBase import Base
from resources.models.Genre import Genre
from resources.models.Release import Release
from resources.models.Track import Track
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
    profile = Column(Text())
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

    artistTracks = relationship(Track, backref="artist")

    userRatings = relationship(UserArtist, cascade="all, delete-orphan", backref="artist")

    associated_artists = relationship("Artist",
                                      secondary="artistAssociation",
                                      primaryjoin="Artist.id==artistAssociation.c.artistId",
                                      secondaryjoin="Artist.id==artistAssociation.c.associatedArtistId",
                                      backref="associatedArtists")

    associated_with_artists = relationship("Artist",
                                           secondary="artistAssociation",
                                           primaryjoin="Artist.id==artistAssociation.c.associatedArtistId",
                                           secondaryjoin="Artist.id==artistAssociation.c.artistId",
                                           backref="associatedWithArtists")

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

    def serialize(self, includes, conn):
        artistReleases = []
        doIncludeThumbnails = includes and 'thumbnails' in includes
        if includes and 'releases' in includes:
            for release in sorted(self.releases, key=lambda r: r.releaseDate):
                artistReleases.append(release.serialize(includes, conn))
        stats = None
        if includes and 'stats' in includes:
            artistSummaries = conn.execute(text(
                "SELECT rm.releaseMediaCount, r.releaseCount, ts.trackCount, ts.duration, " +
                "ts.size, mts.trackCount AS missingTracks " +
                "FROM `artist` a " +
                "INNER JOIN  " +
                "( " +
                "	select a.id as artistId, count(rm.id) as releaseMediaCount " +
                "	From `releasemedia` rm " +
                "	join `release` r on rm.releaseId = r.id " +
                "	join `artist` a on r.artistId = a.id " +
                "	group by a.id " +
                ") as rm ON rm.artistId = a.id " +
                "INNER JOIN  " +
                "( " +
                "	select a.id as artistId, count(r.id) as releaseCount " +
                "	from `release` r  " +
                "	join `artist` a on r.artistId = a.id " +
                "	group by a.id " +
                ") as r ON r.artistId = a.id " +
                "INNER JOIN  " +
                " ( " +
                "	SELECT r.artistId AS artistId, COUNT(1) AS trackCount, " +
                "      SUM(t.duration) AS duration, SUM(t.fileSize) AS size " +
                "	FROM `track` t " +
                "	JOIN `releasemedia` rm ON rm.id = t.releaseMediaId " +
                "	JOIN `release` r ON r.id = rm.releaseId " +
                "	WHERE t.fileName IS NOT NULL " +
                "	GROUP BY r.artistId  " +
                "	) AS ts ON ts.artistId = a.id " +
                "LEFT JOIN  " +
                " ( " +
                "	SELECT r.artistId AS artistId, COUNT(1) AS trackCount " +
                "	FROM `track` t " +
                "	JOIN `releasemedia` rm ON rm.id = t.releaseMediaId " +
                "	JOIN `release` r ON r.id = rm.releaseId " +
                "	WHERE t.fileName IS NULL " +
                "	GROUP BY r.artistId  " +
                "	) AS mts ON mts.artistId = a.id " +
                "WHERE a.roadieId = '" + self.roadieId + "';", autocommit=True)
                                           .columns(trackCount=Integer, releaseMediaCount=Integer, releaseCount=Integer,
                                                    releaseTrackTime=Integer, releaseTrackFileSize=Integer,
                                                    missingTrackCount=Integer)) \
                .fetchone()
            stats = {
                'tracks': artistSummaries[2] if artistSummaries else 0,
                 'releaseMedia': artistSummaries[0] if artistSummaries else 0,
                 'releases': artistSummaries[1] if artistSummaries else 0,
                 'length': formatTimeMillisecondsNoDays(artistSummaries[3]) if artistSummaries else "--:--",
                 'fileSize': sizeof_fmt(artistSummaries[4]) if artistSummaries else "0",
                 'missingTrackCount': (artistSummaries[5] if artistSummaries else 0) or 0
            }
        return {
            'id': self.roadieId,
            'alternateNames': "" if not self.alternateNames else '|'.join(self.alternateNames),
            'amgId': self.amgId,
            'artistType': self.artistType,
            'beginDate': "" if not self.beginDate else self.beginDate.isoformat(),
            'bioContext': self.bioContext,
            'birthDate': "" if not self.birthDate else self.birthDate.isoformat(),
            'createdDate': self.createdDate.isoformat(),
            'endDate': "" if not self.endDate else self.endDate.isoformat(),
            'isLocked': self.isLocked,
            'isniList': "" if not self.isniList else '|'.join(self.isniList),
            'iTunesId': self.iTunesId,
            'lastUpdated': "" if not self.lastUpdated else self.lastUpdated.isoformat(),
            'musicBrainzId': self.musicBrainzId,
            'name': self.name,
            'profile': self.profile,
            'rating': self.rating,
            'realName': self.realName,
            'sortName': self.sortName,
            'spotifyId': self.spotifyId,
            'status': self.status,
            'stats': stats,
            'tags': "" if not self.tags else '|'.join(self.tags),
            'thumbnail': "" if not doIncludeThumbnails or not self.thumbnail else base64.b64encode(
                self.thumbnail).decode('utf-8'),
            'urls': "" if not self.urls else '|'.join(self.urls),
            'releases': artistReleases,
        }
