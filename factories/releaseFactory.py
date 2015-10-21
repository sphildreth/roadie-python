import os
import json
import hashlib
import random
import uuid
import arrow

from sqlalchemy.sql import func, and_, or_, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from sqlalchemy import create_engine, update

from resources.common import *
from resources.models.Artist import Artist
from resources.models.Genre import Genre
from resources.models.Image import Image
from resources.models.Label import Label
from resources.models.Release import Release
from resources.models.ReleaseLabel import ReleaseLabel
from resources.models.ReleaseMedia import ReleaseMedia
from resources.models.Track import Track

from resources.logger import Logger
from searchEngines.artistSearcher import ArtistSearcher

Base = declarative_base()


class ReleaseFactory(object):
    def __init__(self, dbConn, dbSession):
        self.conn = dbConn
        self.session = dbSession
        self.logger = Logger()
        self.searcher = ArtistSearcher()

    def getAllForArtist(self, artist, forceRefresh=False):
        """
        Query Database for a release with the given title, if not found search and if found save and return results
        :type artist: Artist
        """
        if not artist:
            return None
        printableArtistName = artist.name.encode('ascii', 'ignore').decode('utf-8')
        releases = self._getAllFromDatabaseForArtist(artist)
        if not releases or forceRefresh:
            if not releases:
                self.logger.info("Releases For Artist [" + printableArtistName + "] Not Found")
            else:
                self.logger.info("Refreshing Releases For Artist [" + printableArtistName + "]")
            releases = []
            srList = self.searcher.searchForArtistReleases(artist)
            if not srList:
                self.logger.info("Releases For Artist [" + printableArtistName +
                                 "] Not Found")
                return None
            if srList:
                for sr in srList:
                    title = sr.title
                    release = self._createDatabaseModelFromSearchModel(artist, title, sr)
                    self.session.add(release)
                    releases.append(release)
            self.session.commit()
        return releases

    def get(self, artist, title, forceRefresh=False):
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
        if not release or forceRefresh:
            if not release:
                self.logger.info("Release For Artist [" + printableArtistName +
                                 "] Not Found By Title [" + printableTitle + "]")
            else:
                self.logger.info("Refreshing Release [" + printableTitle + "] For Artist [" + printableArtistName)
            release = Release()
            srList = self.searcher.searchForArtistReleases(artist, title)
            if not srList:
                # If no release found see if the release is "Artist ReleaseTitle" as in "The Who Sell Out"
                searchAgainTitle = artist.name + " " + title
                self.logger.info("Release For Artist [" + printableArtistName +
                                 "] Not Found By Title [" + printableTitle + "]: Searching again using [" +
                                 searchAgainTitle.encode('ascii', 'ignore').decode('utf-8') + "]")
                srList = self.searcher.searchForArtistReleases(artist, searchAgainTitle)
                if not srList:
                    self.logger.info("Release For Artist [" + printableArtistName +
                                     "] Not Found By Title [" + printableTitle + "]")
                    return None
            sr = srList[0]
            if sr:
                release = self._createDatabaseModelFromSearchModel(artist, title, sr)
            self.session.add(release)
            self.session.commit()
        return release

    def _createDatabaseModelFromSearchModel(self, artist, title, sr):
        """
        Take the given SearchResult Release Model and create a Database Model
        :type artist: Artist
        :type title: str
        :type sr: searchEngines.models.Release.Release
        """
        release = Release()
        printableTitle = title.encode('ascii', 'ignore').decode('utf-8')
        releaseByExternalIds = self._getFromDatabaseByExternalIds(sr.musicBrainzId,
                                                                  sr.iTunesId,
                                                                  sr.lastFMId,
                                                                  sr.amgId,
                                                                  sr.spotifyId)
        if releaseByExternalIds:
            if not releaseByExternalIds.alternateNames:
                releaseByExternalIds.alternateNames = []
            if title not in releaseByExternalIds.alternateNames:
                self.logger.debug("Found Title By External Ids [" +
                                  releaseByExternalIds.title.encode('ascii', 'ignore')
                                  .decode('utf-8') + "] Added [" +
                                  printableTitle + "] To AlternateNames")
                if not releaseByExternalIds.alternateNames:
                    releaseByExternalIds.alternateNames = []
                releaseByExternalIds.alternateNames.append(title)
                releaseByExternalIds.lastUpdated = arrow.utcnow().datetime
                self.session.commit()
            return releaseByExternalIds
        release.artist = artist
        release.roadieId = sr.roadieId
        release.title = title
        release.releaseDate = parseDate(sr.releaseDate)
        release.random = sr.random
        release.trackCount = sr.trackCount
        release.mediaCount = sr.mediaCount
        release.thumbnail = sr.thumbnail
        release.profile = sr.profile
        # TODO
    #        release.releaseType = sr.releaseType
        release.iTunesId = sr.iTunesId
        release.amgId = sr.amgId
        release.lastFMId = sr.lastFMId
        release.lastFMSummary = sr.lastFMSummary
        release.musicBrainzId = sr.musicBrainzId
        release.spotifyId = sr.spotifyId
        release.amgId = sr.amgId
        release.tags = sr.tags
        release.alternateNames = sr.alternateNames
        release.urls = sr.urls
        if sr.images:
            release.images = []
            for image in sr.images:
                i = Image()
                i.roadieId = image.roadieId
                i.url = image.url
                i.caption = image.caption
                i.image = image.image
                release.images.append(i)

        # TODO
        # See if cover file found in Release Folder
        # coverFile = os.path.join(mp3Folder, "cover.jpg")
        # if os.path.isfile(coverFile):
        #     ba = self.readImageThumbnailBytesFromFile(coverFile)
        # else:
        #     coverFile = os.path.join(mp3Folder, "front.jpg")
        #     if os.path.isfile(coverFile):
        #         ba = self.readImageThumbnailBytesFromFile(coverFile)
        # # if no bytes found see if MusicBrainz has cover art
        # if not ba:
        #     coverArtBytes = mb.lookupCoverArt(release.MusicBrainzId)
        #     if coverArtBytes:
        #         try:
        #             img = Image.open(io.BytesIO(coverArtBytes))
        #             img.thumbnail(self.thumbnailSize)
        #             b = io.BytesIO()
        #             img.save(b, "JPEG")
        #             ba = b.getvalue()
        #         except:
        #             pass
        if sr.genres:
            release.genres = []
            for genre in sr.genres:
                dbGenre = self.session.query(Genre).filter(Genre.name == genre.name).first()
                if not dbGenre:
                    g = Genre()
                    g.name = genre.name
                    g.roadieId = genre.roadieId
                    release.genres.append(g)
                else:
                    release.genres.append(dbGenre)
        if sr.releaseLabels:
            release.releaseLabels = []
            for srReleaseLabel in sr.releaseLabels:
                l = self._getLabelFromDatabase(srReleaseLabel.label.name)
                if not l:
                    l = Label()
                    l.roadieId = srReleaseLabel.label.roadieId
                    l.musicBrainzId = srReleaseLabel.label.musicBrainzId
                    l.beginDate = srReleaseLabel.label.beginDate
                    l.end = srReleaseLabel.label.endDate
                    l.imageUrl = srReleaseLabel.label.imageUrl
                    l.tags = srReleaseLabel.label.tags
                    l.alternateNames = srReleaseLabel.label.alternateNames
                    l.sortName = srReleaseLabel.label.sortName
                    l.name = srReleaseLabel.label.name
                if l:
                    rl = ReleaseLabel()
                    rl.roadieId = srReleaseLabel.roadieId
                    rl.catalogNumber = srReleaseLabel.catalogNumber
                    rl.beginDate = parseDate(srReleaseLabel.beginDate)
                    rl.endDate = parseDate(srReleaseLabel.endDate)
                    rl.label = l
                    if rl not in release.releaseLabels:
                        release.releaseLabels.append(rl)
        if sr.media:
            release.media = []
            for srMedia in sr.media:
                media = ReleaseMedia()
                media.roadieId = srMedia.roadieId
                media.releaseMediaNumber = srMedia.releaseMediaNumber
                media.releaseSubTitle = srMedia.releaseSubTitle
                media.trackCount = srMedia.trackCount
                if srMedia.tracks:
                    media.tracks = []
                    for srTrack in srMedia.tracks:
                        track = Track()
                        track.roadieId = srTrack.roadieId
                        track.partTitles = srTrack.partTitles
                        track.random = srTrack.random
                        track.musicBrainzId = srTrack.musicBrainzId
                        track.amgId = srTrack.amgId
                        track.spotifyId = srTrack.spotifyId
                        track.title = srTrack.title
                        track.trackNumber = srTrack.trackNumber
                        track.duration = srTrack.duration
                        track.tags = srTrack.tags
                        track.alternateNames = []
                        cleanedTitle = createCleanedName(srTrack.title)
                        if cleanedTitle != srTrack.title.lower().strip():
                            track.alternateNames.append(cleanedTitle)
                        media.tracks.append(track)
                release.media.append(media)
        return release

    def _getAllFromDatabaseForArtist(self, artist):
        if not artist:
            return None
        return self.session.query(Release).filter(Release.artistId == artist.id).order_by(Release.releaseDate).all()

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

    def _getLabelFromDatabase(self, name):
        if not name:
            return None
        name = name.lower().strip().replace("'", "''")
        stmt = or_(func.lower(Label.name) == name,
                   text("(lower(alternateNames) == '" + name + "'" + ""
                        " OR alternateNames like '" + name + "|%'" +
                        " OR alternateNames like '%|" + name + "|%'" +
                        " OR alternateNames like '%|" + name + "')"))
        return self.session.query(Label).filter(stmt).first()

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

    def create(self, artist, title, trackCount, releaseDate):
        if not artist or not title or not trackCount or not releaseDate:
            return None
        release = Release()
        release.random = random.randint(1, 9999999)
        release.title = title
        release.releaseDate = parseDate(releaseDate)
        release.trackCount = trackCount
        release.artistId = artist.id
        release.createdDate = arrow.utcnow().datetime
        release.roadieId = str(uuid.uuid4())
        release.alternateNames = []
        cleanedTitle = createCleanedName(title)
        if cleanedTitle != title.lower().strip():
            release.alternateNames.append(cleanedTitle)
        return release

    def add(self, release):
        self.session.add(release)
        self.session.commit()

    def delete(self, release):
        self.session.delete(release)
        self.session.commit()
