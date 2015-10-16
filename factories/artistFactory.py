import arrow
import datetime

from sqlalchemy import create_engine
from sqlalchemy.sql import select, func, and_, or_, not_, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from resources.common import *

from resources.models.Artist import Artist
from resources.models.Image import Image
from resources.models.Genre import Genre

from resources.logger import Logger

from searchEngines.artistSearcher import ArtistSearcher
from searchEngines.models.Artist import ArtistType as SearchArtistType

Base = declarative_base()


class ArtistFactory(object):

    def __init__(self, config):
        engine = create_engine(config['ROADIE_DATABASE_URL'], echo=True)
        Base.metadata.bind = engine
        DBSession = sessionmaker(bind=engine)
        self.session = DBSession()
        self.logger = Logger()
        self.searcher = ArtistSearcher()

    def add(self, artist, newRecord=True):
        """
        Add the Artist to the Database
        :type artist: Artist
        """
        if newRecord:
            doesExist = self._getFromDatabase(artist.name)
            if doesExist:
                appendDate = str(arrow.utcnow().date)
                if artist.beginDate:
                    appendDate = str(artist.beginDate)
                artist.name = artist.name + " (" + appendDate + ")"
                doesExist = self._getFromDatabase(artist.name)
                if doesExist:
                    artist.name = artist.name + " (" + arrow.utcnow().isoformat() + ")"
        self.session.add(artist)
        self.session.commit()
        return artist

    def delete(self, artist):
        """
        Remove the Artist from the Database
        :type artist: Artist
        """
        self.session.delete(artist)
        self.session.commit()

    def _getFromDatabaseByName(self, name):
        if not name:
            return None
        name = name.lower().strip()
        stmt = or_(func.lower(Artist.name) == name,
                   func.lower(Artist.sortName) == name,
                   text("(lower(alternatenames) == '" + name + "'" + ""
                   " OR alternatenames like '" + name + "|%'" +
                   " OR alternatenames like '%|" + name + "|%'" +
                   " OR alternatenames like '%|" + name + "')"))
        return self.session.query(Artist).filter(stmt).first()

    def _getFromDatabaseByExternalIds(self, musicBrainzId, iTunesId, amgId, spotifyId):
        stmt = or_(Artist.musicBrainzId == musicBrainzId,
                   Artist.iTunesId == iTunesId,
                   Artist.amgId == amgId,
                   Artist.spotifyId == spotifyId
                   )
        return self.session.query(Artist).filter(stmt).first()

    def _getFromDatabaseByRoadieId(self,roadieId):
        return self.session.query(Artist).filter(Artist.roadieId == roadieId).first()

    def _saveToDatabase(self, artist):
        self.add(artist, False)
        self.commit()




    def get(self, name):
        """
        Query Database for an artist with the given name, if not found search and if found save and return results
        :type name: str
        """
        if not name:
            return None
        name = deriveArtistFromName(name)
        artist = self._getFromDatabaseByName(name)
        if not artist:
            self.logger.info("Artist Not Found By Name [" + name + "]")
            artist = Artist()
            sa = self.searcher.searchForArtist(name)
            if sa:
                existsByExternalIds = self._getFromDatabaseByExternalIds(sa.musicBrainzId, sa.iTunesId, sa.amgId, sa.spotifyId)
                if existsByExternalIds:
                    if not existsByExternalIds.alternatenames:
                        existsByExternalIds.alternatenames = []
                    existsByExternalIds.alternatenames.append(name)
                    self.logger.debug("Found Artist By External Ids [" + existsByExternalIds.name + "] Added [" + name + "] To AlternateNames")
                    self._saveToDatabase(existsByExternalIds)
                    return existsByExternalIds
                artist.name = sa.name
                artist.roadieId = sa.roadieId
                artist.sortName = sa.sortName
                artist.rating = sa.rating
                artist.random = sa.random
                artist.realName = sa.realName
                artist.musicBrainzId = sa.musicBrainzId
                artist.iTunesId = sa.iTunesId
                artist.amgId = sa.amgId
                artist.spotifyId = sa.spotifyId
                artist.thumbnail = sa.thumbnail
                artist.profile = sa.profile
                if sa.birthDate:
                    artist.birthDate = parseDate(sa.birthDate)
                if sa.beginDate:
                    artist.beginDate = parseDate(sa.beginDate)
                if sa.endDate:
                    artist.endDate = parseDate(sa.endDate)
                if sa.artistType == SearchArtistType.Person:
                    artist.artistType = 'Person'
                elif sa.artistType == SearchArtistType.Group:
                    artist.artistType = 'Group'
                elif sa.artistType == SearchArtistType.Orchestra:
                    artist.artistType = 'Orchestra'
                elif sa.artistType == SearchArtistType.Choir:
                    artist.artistType = 'Choir'
                elif sa.artistType == SearchArtistType.Character:
                    artist.artistType = 'Character'
                artist.bioContext = sa.bioContext
                artist.tags = sa.tags
                if sa.alternateNames:
                    artist.alternateNames = []
                    for an in sa.alternateNames:
                        artist.alternateNames.append(an)
                if sa.urls:
                    artist.urls = []
                    for url in sa.urls:
                        artist.urls.append(url)
                if sa.isniList:
                    artist.isniList = []
                    for isni in sa.isniList:
                        artist.isniList.append(isni)
                if sa.images:
                    artist.images = []
                    for image in sa.images:
                        i = Image()
                        i.url = image.url
                        i.caption = image.caption
                        i.image = image.image
                        artist.images.append(i)
                if sa.genres:
                    artist.genres = []
                    for genre in sa.genres:
                        dbGenre = self.session.query(Genre).filter(Genre.name == genre.name).first()
                        if not dbGenre:
                            g = Genre()
                            g.name = genre.name
                            artist.genres.append(g)
                        else:
                            artist.genres.append(dbGenre)
                self.session.add(artist)
                self.session.commit()

        return artist

