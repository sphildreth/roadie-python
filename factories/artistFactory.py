import random
import uuid

from sqlalchemy.sql import func, and_, or_, text

from resources.common import *
from resources.models.Artist import Artist
from resources.models.Image import Image
from resources.models.Genre import Genre
from resources.logger import Logger
from searchEngines.artistSearcher import ArtistSearcher
from searchEngines.models.Artist import ArtistType as SearchArtistType


class ArtistFactory(object):
    def __init__(self, dbConn, dbSession):
        self.conn = dbConn
        self.session = dbSession
        self.logger = Logger()
        self.searcher = ArtistSearcher()

    def add(self, artist, newRecord=True):
        """
        Add the Artist to the Database
        :type artist: Artist
        """
        if newRecord:
            doesExist = self._getFromDatabaseByName(artist.name)
            if doesExist:
                # Ensure that tthere is only one with the name append the BeginDate if not unique
                appendDate = str(arrow.utcnow().date)
                if artist.beginDate:
                    appendDate = str(artist.beginDate)
                artist.name = artist.name + " (" + appendDate + ")"
                doesExist = self._getFromDatabaseByName(artist.name)
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
        name = name.lower().strip().replace("'", "''")
        stmt = or_(func.lower(Artist.name) == name,
                   func.lower(Artist.sortName) == name,
                   text("(lower(alternateNames) == '" + name + "'" + ""
                                                                     " OR alternateNames like '" + name + "|%'" +
                        " OR alternateNames like '%|" + name + "|%'" +
                        " OR alternateNames like '%|" + name + "')"))
        return self.session.query(Artist).filter(stmt).first()

    def _getFromDatabaseByExternalIds(self, musicBrainzId, iTunesId, amgId, spotifyId):
        mb = and_(Artist.musicBrainzId == musicBrainzId, musicBrainzId is not None)
        it = and_(Artist.iTunesId == iTunesId, iTunesId is not None)
        ag = and_(Artist.amgId == amgId, amgId is not None)
        sp = and_(Artist.spotifyId == spotifyId, spotifyId is not None)
        stmt = or_(mb, it, ag, sp)
        return self.session.query(Artist).filter(stmt).first()

    def _getFromDatabaseByRoadieId(self, roadieId):
        return self.session.query(Artist).filter(Artist.roadieId == roadieId).first()

    def _saveToDatabase(self, artist):
        artist.lastUpdated = arrow.utcnow().datetime
        self.session.commit()

    def get(self, name):
        """
        Query Database for an artist with the given name, if not found search and if found save and return results
        :type name: str
        """
        if not name:
            return None
        try:
            name = deriveArtistFromName(name)
            printableName = name.encode('ascii', 'ignore').decode('utf-8')
            artist = self._getFromDatabaseByName(name)
            if not artist:
                self.logger.info("Artist Not Found By Name [" + printableName + "]")
                artist = Artist()
                sa = self.searcher.searchForArtist(name)
                if not sa:
                    artist.name = name
                    artist.random = random.randint(1, 9999999)
                    artist.createdDate = arrow.utcnow().datetime
                    artist.roadieId = str(uuid.uuid4())
                    artist.alternateNames = []
                    cleanedArtistName = createCleanedName(name)
                    if cleanedArtistName != name.lower().strip():
                        artist.alternateNames.append(cleanedArtistName)
                else:
                    artistByExternalIds = self._getFromDatabaseByExternalIds(sa.musicBrainzId, sa.iTunesId, sa.amgId,
                                                                             sa.spotifyId)
                    if artistByExternalIds:
                        if not artistByExternalIds.alternateNames:
                            artistByExternalIds.alternateNames = []
                        if name not in artistByExternalIds.alternateNames:
                            self.logger.debug("Found Artist By External Ids [" +
                                              artistByExternalIds.name.encode('ascii', 'ignore')
                                              .decode('utf-8') + "] Added [" +
                                              printableName + "] To AlternateNames")
                            artistByExternalIds.alternateNames.append(name)
                            artistByExternalIds.lastUpdated = arrow.utcnow().datetime
                            self.session.commit()
                        return artistByExternalIds
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
                            if image.image:
                                i = Image()
                                i.url = image.url
                                i.roadieId = image.roadieId
                                i.caption = image.caption
                                i.signature = image.signature
                                i.image = image.image
                                artist.images.append(i)
                        if not artist.thumbnail and artist.images:
                            artist.thumbnail = artist.images[0].image
                    # TODO
                    # # See if a file exists to use for the Artist thumbnail
                    # artistFile = os.path.join(mp3Folder, "artist.jpg")
                    # if os.path.exists(artistFile):
                    #     ba = self.readImageThumbnailBytesFromFile(artistFile)
                    # if ba:
                    #     artist.Thumbnail.new_file()
                    #     artist.Thumbnail.write(ba)
                    #     artist.Thumbnail.close()

                    if sa.genres:
                        artist.genres = []
                        for genre in sa.genres:
                            dbGenre = self.session.query(Genre).filter(Genre.name == genre.name).first()
                            if not dbGenre:
                                g = Genre()
                                g.name = genre.name
                                g.roadieId = genre.roadieId
                                artist.genres.append(g)
                            else:
                                artist.genres.append(dbGenre)
                    self.session.add(artist)
                    self.session.commit()
            return artist
        except:
            self.logger.exception("ArtistFactory: Error In get()")
            pass
        return None
