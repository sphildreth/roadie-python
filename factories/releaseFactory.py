import os
import uuid

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func, and_, or_, text

from resources.common import *
from resources.logger import Logger
from resources.models.Artist import Artist
from resources.models.Genre import Genre
from resources.models.Image import Image
from resources.models.Label import Label
from resources.models.Release import Release
from resources.models.ReleaseLabel import ReleaseLabel
from resources.models.ReleaseMedia import ReleaseMedia
from resources.models.Track import Track
from searchEngines.artistSearcher import ArtistSearcher
from searchEngines.models.Release import ReleaseType as SearchReleaseType

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
        :param artist: Artist
        :param forceRefresh: bool
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
            srList = self.searcher.searchForArtistReleases(artist, [])
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

    def get(self, artist, title, doFindIfNotInDB=True, forceRefresh=False):
        """
        Query Database for a release with the given title, if not found search and if found save and return results
        :param forceRefresh: bool
        :param doFindIfNotInDB: bool
        :rtype : Release
        :param artist: Artist
        :param title: str
        """
        try:
            if not title or not artist:
                return None
            startTime = arrow.utcnow().datetime
            printableTitle = title.encode('ascii', 'ignore').decode('utf-8')
            printableArtistName = artist.name.encode('ascii', 'ignore').decode('utf-8')
            release = self._getFromDatabaseByTitle(artist, title)
            if not release and doFindIfNotInDB or forceRefresh:
                if not release:
                    self.logger.info("Release For Artist [" + printableArtistName +
                                     "] Not Found By Title [" + printableTitle + "]")
                else:
                    self.logger.info("Refreshing Release [" + printableTitle + "] For Artist [" + printableArtistName)
                release = Release()
                artistReleaseImages = self.session.query(Image) \
                    .add_column(Image.signature) \
                    .join(Release) \
                    .filter(Release.artistId == artist.id).all()
                srList = self.searcher.searchForArtistReleases(artist, artistReleaseImages, title)
                if not srList:
                    self.logger.info("Release For Artist [" + printableArtistName +
                                     "] Not Found By Title [" + printableTitle + "]")
                    return None
                sr = srList[0]
                if sr:
                    release = self._createDatabaseModelFromSearchModel(artist, title, sr)
                self.session.add(release)
                self.session.commit()
            elapsedTime = arrow.utcnow().datetime - startTime
            self.logger.info(": ReleaseFactory get elapsed time [" + str(elapsedTime) + "]")
            return release
        except:
            self.logger.exception("ReleaseFactory: Error In get()")
            pass
        return None

    def _createDatabaseModelFromSearchModel(self, artist, title, sr):
        """
        Take the given SearchResult Release Model and create a Database Model
        :type artist: Artist
        :type title: str
        :type sr: searchEngines.models.Release.Release
        """
        createDattabaseModelFromSearchModelRelease = Release()
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
        createDattabaseModelFromSearchModelRelease.artist = artist
        createDattabaseModelFromSearchModelRelease.roadieId = sr.roadieId
        createDattabaseModelFromSearchModelRelease.title = title
        createDattabaseModelFromSearchModelRelease.releaseDate = parseDate(sr.releaseDate)
        createDattabaseModelFromSearchModelRelease.trackCount = sr.trackCount
        createDattabaseModelFromSearchModelRelease.mediaCount = sr.mediaCount
        createDattabaseModelFromSearchModelRelease.thumbnail = sr.thumbnail
        createDattabaseModelFromSearchModelRelease.profile = sr.profile
        if sr.releaseType == SearchReleaseType.Album:
            createDattabaseModelFromSearchModelRelease.releaseType = 'Album'
        elif sr.releaseType == SearchReleaseType.EP:
            createDattabaseModelFromSearchModelRelease.releaseType = 'EP'
        elif sr.releaseType == SearchReleaseType.Single:
            createDattabaseModelFromSearchModelRelease.releaseType = 'Single'
        createDattabaseModelFromSearchModelRelease.iTunesId = sr.iTunesId
        createDattabaseModelFromSearchModelRelease.amgId = sr.amgId
        createDattabaseModelFromSearchModelRelease.lastFMId = sr.lastFMId
        createDattabaseModelFromSearchModelRelease.lastFMSummary = sr.lastFMSummary
        createDattabaseModelFromSearchModelRelease.musicBrainzId = sr.musicBrainzId
        createDattabaseModelFromSearchModelRelease.spotifyId = sr.spotifyId
        createDattabaseModelFromSearchModelRelease.amgId = sr.amgId
        createDattabaseModelFromSearchModelRelease.tags = sr.tags
        createDattabaseModelFromSearchModelRelease.alternateNames = sr.alternateNames

        createDattabaseModelFromSearchModelRelease.urls = sr.urls
        if sr.images:
            createDattabaseModelFromSearchModelReleaseimages = []
            for image in sr.images:
                if image.image:
                    i = Image()
                    i.roadieId = image.roadieId
                    i.url = image.url
                    i.caption = image.caption
                    i.image = image.image
                    i.signature = image.signature
                    createDattabaseModelFromSearchModelReleaseimages.append(i)
            createDattabaseModelFromSearchModelRelease.images = createDattabaseModelFromSearchModelReleaseimages
            self.logger.debug(
                "= Added [" + str(len(createDattabaseModelFromSearchModelRelease.images)) + "] Images to Release")

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
            createDattabaseModelFromSearchModelRelease.genres = []
            for genre in sr.genres:
                dbGenre = self.session.query(Genre).filter(Genre.name == genre.name).first()
                if not dbGenre:
                    g = Genre()
                    g.name = genre.name
                    g.roadieId = genre.roadieId
                    createDattabaseModelFromSearchModelRelease.genres.append(g)
                else:
                    createDattabaseModelFromSearchModelRelease.genres.append(dbGenre)
        if sr.releaseLabels:
            createDattabaseModelFromSearchModelRelease.releaseLabels = []
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
                    if srReleaseLabel.label.alternateNames:
                        srLabelAlternateNames = []
                        for srLabelAn in srReleaseLabel.label.alternateNames:
                            srLabelAlternateNames.append(srLabelAn.replace("|", ","))
                        l.alternateNames = srLabelAlternateNames
                    l.sortName = srReleaseLabel.label.sortName
                    l.name = srReleaseLabel.label.name
                if l:
                    rl = ReleaseLabel()
                    rl.roadieId = srReleaseLabel.roadieId
                    rl.catalogNumber = srReleaseLabel.catalogNumber
                    rl.beginDate = parseDate(srReleaseLabel.beginDate)
                    rl.endDate = parseDate(srReleaseLabel.endDate)
                    rl.label = l
                    if rl not in createDattabaseModelFromSearchModelRelease.releaseLabels:
                        createDattabaseModelFromSearchModelRelease.releaseLabels.append(rl)
        if sr.media:
            createDattabaseModelFromSearchModelRelease.media = []
            for srMedia in sr.media:
                media = ReleaseMedia()
                media.roadieId = srMedia.roadieId
                media.releaseMediaNumber = int(srMedia.releaseMediaNumber)
                # The first media is release 1 not release 0
                if media.releaseMediaNumber < 1:
                    media.releaseMediaNumber = 1
                media.releaseSubTitle = srMedia.releaseSubTitle
                media.trackCount = srMedia.trackCount
                if srMedia.tracks:
                    media.tracks = []
                    for srTrack in srMedia.tracks:
                        track = Track()
                        track.roadieId = srTrack.roadieId
                        track.partTitles = srTrack.partTitles
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
                createDattabaseModelFromSearchModelRelease.media.append(media)
            createDattabaseModelFromSearchModelRelease.mediaCount = len(
                createDattabaseModelFromSearchModelRelease.media)
        return createDattabaseModelFromSearchModelRelease

    def _getAllFromDatabaseForArtist(self, artist):
        if not artist:
            return None
        return self.session.query(Release).filter(Release.artistId == artist.id).order_by(Release.releaseDate).all()

    def _getFromDatabaseByTitle(self, artist, title):
        if not title:
            return None
        title = title.lower().strip()
        cleanedTitle = createCleanedName(title)
        stmt = or_(func.lower(Release.title) == title,
                   text("(lower(alternateNames) = '" + title.replace("'", "''") + "'" + ""
                                                                                        " OR alternateNames like '" + title.replace(
                       "'", "''") + "|%'" +
                        " OR alternateNames like '%|" + title.replace("'", "''") + "|%'" +
                        " OR alternateNames like '%|" + title.replace("'", "''") + "')"),
                   text("(alternateNames = '" + cleanedTitle + "'" + ""
                                                                     " OR alternateNames like '" + cleanedTitle + "|%'" +
                        " OR alternateNames like '%|" + cleanedTitle + "|%'" +
                        " OR alternateNames like '%|" + cleanedTitle + "')")
                   )
        return self.session.query(Release).filter(Release.artistId == artist.id).filter(stmt).first()

    def _getLabelFromDatabase(self, name):
        if not name:
            return None
        name = name.lower().strip()
        stmt = or_(func.lower(Label.name) == name,
                   text("(lower(alternateNames) = '" + name.replace("'", "''") + "'" + ""
                                                                                       " OR alternateNames like '" + name.replace(
                       "'", "''") + "|%'" +
                        " OR alternateNames like '%|" + name.replace("'", "''") + "|%'" +
                        " OR alternateNames like '%|" + name.replace("'", "''") + "')"))
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

    def delete(self, release, pathToTrack, deleteFiles=False):
        """
        Performs all necessary steps to delete a Release and optionally Release Tracks
        :param pathToTrack: Method to generate Full Path for Release Media Tracks
        :param release: Releasesaasdf
        :type deleteFiles: bool
        """
        if not release:
            return False
        try:
            if deleteFiles:
                try:
                    for deleteReleaseMedia in release.media:
                        for track in deleteReleaseMedia.tracks:
                            trackPath = pathToTrack(track)
                            trackFolder = os.path.dirname(trackPath)
                            os.remove(trackPath)
                            # if the folder is empty then delete the folder as well
                            if trackFolder:
                                if not os.listdir(trackFolder):
                                    os.rmdir(trackFolder)
                except OSError:
                    pass
            release.genres = []
            self.session.commit()
            self.session.delete(release)
            self.session.commit()
            return True
        except:
            self.session.rollback()
            self.logger.exception("Error Deleting Release")
        return False
