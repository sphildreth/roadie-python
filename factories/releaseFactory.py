from sqlalchemy.sql import func, and_, or_, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from sqlalchemy import create_engine, update

from resources.common import *
from resources.models.Artist import Artist
from resources.models.Collection import Collection
from resources.models.CollectionRelease import CollectionRelease
from resources.models.Genre import Genre
from resources.models.Image import Image
from resources.models.Label import Label
from resources.models.Playlist import Playlist
from resources.models.PlaylistTrack import PlaylistTrack
from resources.models.Release import Release
from resources.models.ReleaseLabel import ReleaseLabel
from resources.models.ReleaseMedia import ReleaseMedia
from resources.models.Track import Track
from resources.models.User import User
from resources.models.UserArtist import UserArtist
from resources.models.UserRelease import UserRelease
from resources.models.UserRole import UserRole
from resources.models.UserTrack import UserTrack

from resources.logger import Logger
from searchEngines.artistSearcher import ArtistSearcher

Base = declarative_base()


class ReleaseFactory(object):
    def __init__(self, config):
        engine = create_engine(config['ROADIE_DATABASE_URL'], echo=True)
        self.conn = engine.connect()
        Base.metadata.bind = engine
        DBSession = sessionmaker(bind=engine)
        self.session = DBSession()
        self.logger = Logger()
        self.searcher = ArtistSearcher()

    def get(self, artist, title):
        """
        Query Database for a release with the given title, if not found search and if found save and return results
        :type artist: Artist
        :type title: str
        """
        if not title or not artist:
            return None
        printableTitle = title.encode('ascii', 'ignore').decode('utf-8')
        printableArtistName = artist.name.encode('ascii', 'ignore').decode('utf-8')
        release = self._getFromDatabaseByTitle(title)
        if not release:
            self.logger.info("Release For Artist [" + printableArtistName +
                             "] Not Found By Title [" + printableTitle + "]")
            release = Release()
            sr = self.searcher.searchForArtistReleases(artist, title)
            if sr:
                releaseByExternalIds = self._getFromDatabaseByExternalIds(sr.musicBrainzId,
                                                                          sr.iTunesId,
                                                                          sr.lastFMId,
                                                                          sr.amgId,
                                                                          sr.spotifyId)
                if releaseByExternalIds:
                    if not releaseByExternalIds.alternateNames:
                        releaseByExternalIds.alternateNames = []
                    if title not in releaseByExternalIds.alternateNames:
                        releaseByExternalIds.alternateNames.append(title)
                        self.logger.debug("Found Title By External Ids [" +
                                          releaseByExternalIds.name.encode('ascii', 'ignore')
                                          .decode('utf-8') + "] Added [" +
                                          printableTitle + "] To AlternateNames")
                        stmt = update(Release.__table__).where(Release.id == releaseByExternalIds.id) \
                            .values(lastUpdated=arrow.utcnow().datetime,
                                    alternateNames=releaseByExternalIds.alternateNames)
                        self.conn.execute(stmt)
                    return releaseByExternalIds

                # TODO Setup new Release and all its related records


                self.session.add(release)
                self.session.commit()
            return release

    def _getFromDatabaseByTitle(self, title):
        if not title:
            return None
        title = title.lower().strip().replace("'", "''")
        stmt = or_(func.lower(Release.title) == title,
                   text("(lower(alternateNames) == '" + title + "'" + ""
                        " OR alternateNames like '" + title + "|%'" +
                        " OR alternateNames like '%|" + title + "|%'" +
                        " OR alternateNames like '%|" + title + "')"))
        return self.session.query(Release).filter(stmt).first()

    def _getFromDatabaseByExternalIds(self, musicBrainzId, iTunesId, lastFMId, amgId, spotifyId):
        mb = and_(Release.musicBrainzId == musicBrainzId, musicBrainzId is not None)
        it = and_(Release.iTunesId == iTunesId, iTunesId is not None)
        lf = and_(Release.lastFMId == lastFMId, lastFMId is not None)
        ag = and_(Release.amgId == amgId, amgId is not None)
        sp = and_(Release.spotifyId == spotifyId, spotifyId is not None)
        stmt = or_(mb, it, lf, ag, sp)
        return self.session.query(Release).filter(stmt).first()

    def _getFromDatabaseByRoadieId(self, roadieId):
        return self.session.query(Release).filter(Release.roadieId == roadieId).first()

    def add(self, release):
        pass

    def delete(self, release):
        pass