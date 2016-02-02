import os
import uuid
from sqlalchemy import update
from resources.common import *
from resources.models.Release import Release
from resources.models.ReleaseMedia import ReleaseMedia
from resources.models.Track import Track
from resources.id3 import ID3
from resources.logger import Logger
from resources.processingBase import ProcessorBase


class Scanner(ProcessorBase):
    def __init__(self, config, dbConn, dbSession, artistFactory, readOnly, logger=None):
        self.config = config
        self.artistFactory = artistFactory
        self.thumbnailSize = config['ROADIE_THUMBNAILS']['Height'], config['ROADIE_THUMBNAILS']['Width']
        self.readOnly = readOnly or False
        self.logger = logger or Logger()
        self.conn = dbConn
        self.dbSession = dbSession
        super().__init__(config, self.logger)

    @staticmethod
    def inboundMp3Files(folder):
        for root, dirs, files in os.walk(folder):
            for filename in files:
                if os.path.splitext(filename)[1] == ".mp3":
                    yield os.path.join(root, filename)

    @staticmethod
    def mp3FileCountForRelease(artistFolder, release):
        try:
            mp3FileCountForRelease = 0
            checkedFolders = []
            for media in release.media:
                for track in media.tracks:
                    fullMediaPath = os.path.join(artistFolder, track.filePath)
                    if fullMediaPath not in checkedFolders:
                        mp3FileCountForRelease += Scanner.mp3FileCountForFolder(fullMediaPath)
                        checkedFolders.append(fullMediaPath)
            return mp3FileCountForRelease
        except:
            pass
        return 0

    @staticmethod
    def mp3FileCountForFolder(folder):
        try:
            return len([f for f in os.listdir(folder)
                        if f.endswith('.mp3') and os.path.isfile(os.path.join(folder, f))])
        except:
            pass
        return 0

    def _markTrackMissing(self, track, fileName):
        if not self.readOnly:
            track.filePath = None
            track.fileName = None
            track.fileSize = 0
            track.hash = None
            track.lastUpdated = arrow.utcnow().datetime
        self.logger.warn("x Marked Track Missing [" + track.title + "]: File [" + fileName + "] Not Found.")

    def scan(self, folder, artist, release):
        """
        Scan the given folder and update, insert or mark missing track information
        :param folder: str
        :param artist: Artist
        :param release: Release
        :return: int
        """
        if self.readOnly:
            self.logger.debug("[Read Only] Would Process Folder [" + folder + "] With Artist [" + str(artist) + "]")
            return None
        if not artist:
            self.logger.debug("! scanner.scan given Invalid Artist")
            raise RuntimeError("Invalid Artist")
        if not release:
            self.logger.debug("! scanner.scan given Invalid Release")
            raise RuntimeError("Invalid Release")
        if not folder:
            self.logger.debug("! scanner.scan given Invalid Folder")
            raise RuntimeError("Invalid Folder")
        folderHead, folderTail = os.path.split(folder)
        folderHeadNoLibrary = folderHead.replace(self.config['ROADIE_LIBRARY_FOLDER'], "")
        trackFilePath = os.path.join(folderHeadNoLibrary, folderTail)
        startTime = arrow.utcnow().datetime
        self.logger.info("-> Scanning Folder [" + folder + "] " +
                         "Artist Folder [" + self.artistFolder(artist) + "] ")
        # Get any existing tracks for folder and verify; update if ID3 tags are different
        if not self.readOnly:
            existingTracksChecked = 0
            for track in self.dbSession.query(Track).filter(Track.filePath == trackFilePath).all():
                existingTracksChecked += 1
                filename = self.pathToTrack(track)
                # File no longer exists for track
                if not os.path.isfile(filename):
                    if not self.readOnly:
                        self._markTrackMissing(track, filename)
                else:
                    id3 = ID3(filename)
                    # File has invalid ID3 tags now
                    if not id3.isValid():
                        self.logger.warn("! Track Has Invalid or Missing ID3 Tags [" + filename + "]")
                        if not self.readOnly:
                            try:
                                os.remove(filename)
                            except OSError:
                                pass
                            self._markTrackMissing(track, filename)
                    else:
                        try:
                            id3Hash = self.makeTrackHash(artist.roadieId, str(id3))
                            if id3Hash != track.Hash:
                                if not self.readOnly:
                                    self.logger.warn("x Hash Mismatch [" + track.Title + "]")
                                    self._markTrackMissing(track, filename)
                        except:
                            pass
            self.logger.debug(
                    "-- Checked [" + str(existingTracksChecked) + "] Existing Tracks for [" + str(trackFilePath) + "]")

        # For each file found in folder get ID3 info and insert record into Track DB
        foundReleaseTracks = 0
        createdReleaseTracks = 0
        scannedMp3Files = 0
        releaseMediaTrackCount = 0
        for mp3 in self.inboundMp3Files(folder):
            id3 = ID3(mp3)
            if id3 is not None:
                cleanedTitle = createCleanedName(id3.title)
                if not id3.isValid():
                    self.logger.warn("! Track Has Invalid or Missing ID3 Tags [" + mp3 + "]")
                else:
                    head, tail = os.path.split(mp3)
                    headNoLibrary = head.replace(self.config['ROADIE_LIBRARY_FOLDER'], "")
                    trackHash = self.makeTrackHash(artist.roadieId, str(id3))
                    track = None
                    mp3FileSize = os.path.getsize(mp3)
                    id3MediaNumber = id3.disc
                    # The first media is release 1 not release 0
                    if id3MediaNumber < 1:
                        id3MediaNumber = 1
                    releaseMedia = None
                    for releaseMediaFind in release.media:
                        if releaseMediaFind.releaseMediaNumber == id3MediaNumber:
                            releaseMedia = releaseMediaFind
                            for releaseTrack in releaseMediaFind.tracks:
                                if isEqual(releaseTrack.trackNumber, id3.track) or isEqual(releaseTrack.hash,
                                                                                           trackHash):
                                    track = releaseTrack
                                    releaseMediaTrackCount = releaseMediaFind.trackCount
                                    break
                                else:
                                    continue
                                break
                            else:
                                continue
                            break
                    if not track:
                        # If the track isn't found on the release media see if it exists on another and move it
                        existingTrackByHash = self.dbSession.query(Track).filter(Track.hash == trackHash).first()
                        if existingTrackByHash:
                            track = existingTrackByHash
                            if releaseMedia:
                                oldMediaId = track.releaseMediaId
                                track.releaseMediaId = releaseMedia.id
                                self.logger.warn("=> Moved Track Id [" + str(track.id) + "] " +
                                                 "to ReleaseMedia Id [" + str(releaseMedia.id) + "] " +
                                                 "was on ReleaseMedia Id [" + str(oldMediaId) + "]")
                    if not track:
                        createdReleaseTracks += 1
                        if not releaseMedia:
                            releaseMedia = ReleaseMedia()
                            releaseMedia.tracks = []
                            releaseMedia.status = 1
                            releaseMedia.trackCount = 1
                            releaseMedia.releaseMediaNumber = id3MediaNumber
                            releaseMedia.roadieId = str(uuid.uuid4())
                            if not release.media:
                                release.media = []
                            release.media.append(releaseMedia)
                            release.mediaCount = len(release.media)
                            self.logger.info("+ Added ReleaseMedia [" + str(releaseMedia.info()) + "] To Release")
                        track = Track()
                        track.fileName = tail
                        track.filePath = headNoLibrary
                        track.hash = trackHash
                        track.fileSize = mp3FileSize
                        track.createdDate = arrow.utcnow().datetime
                        track.roadieId = str(uuid.uuid4())
                        track.title = id3.title
                        track.trackNumber = id3.track
                        track.duration = int(id3.length) * 1000
                        track.status = 1
                        track.partTitles = []
                        if id3.hasTrackArtist():
                            shouldMakeArtistIfNotFound = not release.isCastRecording()
                            ta = id3.getTrackArtist()
                            trackArtist = self.artistFactory.get(ta, shouldMakeArtistIfNotFound)
                            if trackArtist:
                                track.artistId = trackArtist.id
                            elif not shouldMakeArtistIfNotFound:
                                track.partTitles.append(ta)
                                self.logger.info("+ Added Track PartTitle [" + str(ta) + "]")
                            if id3.artists:
                                ta = "/".join(id3.artists)
                                track.partTitles.append(ta)
                                self.logger.info("+ Added Track PartTitle [" + str(ta) + "]")
                        track.tags = []
                        track.alternateNames = []
                        if cleanedTitle != id3.title.lower().strip():
                            track.alternateNames.append(cleanedTitle)
                        releaseMedia.tracks.append(track)
                        releaseMedia.trackCount += 1
                        releaseMediaTrackCount = releaseMedia.trackCount
                        self.logger.info("+ Added Track [" + str(track.info()) + "] To ReleaseMedia")

                    elif not self.readOnly:
                        foundReleaseTracks += 1
                        try:
                            trackFullPath = self.pathToTrack(track)
                            isFilePathSame = os.path.samefile(trackFullPath, mp3)
                        except:
                            trackFullPath = None
                            isFilePathSame = False
                        isFileSizeSame = isEqual(track.fileSize, mp3FileSize)
                        isHashSame = isEqual(track.hash, trackHash)
                        if not isFilePathSame or not isFileSizeSame or not isHashSame:
                            track.fileName = tail
                            track.filePath = headNoLibrary
                            track.fileSize = mp3FileSize
                            track.hash = trackHash
                            track.lastUpdated = arrow.utcnow().datetime
                            release.lastUpdated = track.lastUpdated
                            if releaseMedia:
                                releaseMedia.lastUpdated = track.lastUpdated
                            if not track.alternateNames:
                                track.alternateNames = []
                            if cleanedTitle != track.title.lower().strip() and cleanedTitle not in track.alternateNames:
                                track.alternateNames.append(cleanedTitle)
                            self.logger.info("* Updated Track [" + str(track.info()) + "]: " +
                                             "isFilePathSame [" + str(
                                    isFilePathSame) + "] (" + str(trackFullPath) + ":" + str(mp3) + ") " +
                                             "isFileSizeSame [" + str(
                                    isFileSizeSame) + "] (" + str(track.fileSize) + ":" + str(mp3FileSize) + ") " +
                                             "isHashSame [" + str(
                                    isHashSame) + "] (" + str(track.hash) + ":" + str(trackHash) + ") ")
                    scannedMp3Files += 1

        elapsedTime = arrow.utcnow().datetime - startTime
        mp3FilesInFolder = self.mp3FileCountForFolder(folder)
        if mp3FilesInFolder == releaseMediaTrackCount:
            release.libraryStatus = 'Complete'
            if release.trackCount == 0:
                release.trackCount = mp3FilesInFolder
        elif not mp3FilesInFolder:
            release.libraryStatus = 'Missing'
        else:
            release.libraryStatus = 'Incomplete'

        self.logger.info("<- Scanning Folder [" + str(folder.encode('utf-8')) + "] " +
                         "Complete, Scanned [" + ('%02d' % scannedMp3Files) + "] " +
                         "Mp3 Files: Created [" + str(createdReleaseTracks) + "] Release Tracks, " +
                         "Found [" + str(foundReleaseTracks) + "] Release Tracks. " +
                         "Exist in Release Folder [" + str(mp3FilesInFolder) + "] " +
                         "Elapsed Time [" + str(elapsedTime) + "]")
        return scannedMp3Files
