from sqlalchemy import Column, Enum, ForeignKey, Index, Table, Integer, SmallInteger, Boolean, BLOB, String, Date, Text
from sqlalchemy_utils import ScalarListType
from sqlalchemy.orm import relationship

from resources.models.ModelBase import Base
from resources.models.Genre import Genre
from resources.models.CollectionRelease import CollectionRelease
from resources.models.ReleaseLabel import ReleaseLabel
from resources.models.ReleaseMedia import ReleaseMedia
from resources.models.UserRelease import UserRelease
from resources.models.Image import Image

releaseGenreTable = Table('releaseGenreTable', Base.metadata,
                          Column('releaseId', Integer, ForeignKey('release.id')),
                          Column('genreId', Integer, ForeignKey('genre.id')),
                          Index("idx_releaseGenreTableReleaseAndGenre", "releaseId", "genreId")
                          )


class Release(Base):
    # This is set to true to indicate the tracks on this Release are physically on other releases
    isVirtual = Column(Boolean(), default=False)
    title = Column(String(500), nullable=False, index=True)
    alternateNames = Column(ScalarListType(separator="|"))
    releaseDate = Column(Date())
    # Calculated when a user rates an artist based on average User Ratings and stored here for performance
    rating = Column(SmallInteger(), nullable=False, default=0)
    # A random number generated at generation and then used to select random releases
    random = Column(Integer, nullable=False, default=0, index=True)
    # Number of Tracks that should be for all Release Media for this Release
    trackCount = Column(SmallInteger(), nullable=False)
    # Number of Release Media (CDs or LPs) for this Release
    mediaCount = Column(SmallInteger(), default=1)
    thumbnail = Column(BLOB())
    profile = Column(String(2000))
    releaseType = Column(Enum('Album', 'EP', 'Single', 'Unknown', name='releaseType'), default='Album')
    # Flag if all tracks are found (Complete), missing some tracks (Incomplete),
    #     no Folder Found/Missing All Tracks (Missing) or Missing and Wished for (Wishlist)
    libraryStatus = Column(Enum('Complete', 'Incomplete', 'Missing', 'Wishlist', name='releaseType'), default='Missing')
    iTunesId = Column(String(100))
    amgId = Column(String(100))
    lastFMId = Column(String(100))
    lastFMSummary = Column(Text())
    musicBrainzId = Column(String(100))
    spotifyId = Column(String(100))
    tags = Column(ScalarListType(separator="|"))
    urls = Column(ScalarListType(separator="|"))

    artistId = Column(Integer, ForeignKey("artist.id"))
    genres = relationship(Genre, secondary=releaseGenreTable)
    releaseLabels = relationship(ReleaseLabel, backref="release")
    media = relationship(ReleaseMedia, backref="release")
    images = relationship(Image, backref="release")
    userRatings = relationship(UserRelease, backref="release")
    collections = relationship(CollectionRelease, backref="release")

    def isLiveOrCompilation(self):
        """
        Determine if the release is a Live or Compilation album

        """
        try:
            if self.tags:
                for tag in self.tags:
                    if tag and (tag.lower() == "live" or tag.lower() == "compilation"):
                        return True
            if self.genres:
                for genre in self.genres:
                    if genre and (genre.name.lower() == "live" or genre.name.lower() == "compilation"):
                        return True
        except:
            pass
        return False

    def __unicode__(self):
        return self.title

    def info(self):
        return "Id [" + str(self.id) + "], RoadieId [" + str(self.roadieId) +\
                "], AlternateNames [" + "|".join(self.alternateNames or []) + "], Tags [" + "|".join(self.tags or []) + \
               "], MusicBrainzId [" + str(self.musicBrainzId) + "], ITunesId [" + str(self.iTunesId) + \
               "], SpotifyId [" + str(self.spotifyId) + "], AmgId [" + str(self.amgId) \
               + "],LastFMId [" + str(self.lastFMId) + "], ReleaseDate [" + \
               str(self.releaseDate) + "], TrackCount [" + str(self.trackCount) +\
               "], Title [" + str(self.title) + "]"

Index("idx_releaseArtistAndTitle", Release.artistId, Release.title, unique=True)


