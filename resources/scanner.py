import os
import hashlib
import uuid

from sqlalchemy import update

from resources.common import *
from resources.models.ReleaseMedia import ReleaseMedia
from resources.models.Track import Track
from resources.id3 import ID3
from resources.logger import Logger
from resources.processingBase import ProcessorBase


class Scanner(ProcessorBase):
    def __init__(self, config, dbConn, dbSession, readOnly):
        self.config = config
        self.thumbnailSize = config['ROADIE_THUMBNAILS']['Height'], config['ROADIE_THUMBNAILS']['Width']
        self.libraryFolder = config['ROADIE_LIBRARY_FOLDER']
        self.readOnly = readOnly or False
        self.logger = Logger()
        self.conn = dbConn
        self.dbSession = dbSession

    @staticmethod
    def inboundMp3Files(folder):
        for root, dirs, files in os.walk(folder):
            for filename in files:
                if os.path.splitext(filename)[1] == ".mp3":
                    yield os.path.join(root, filename)

    def _markTrackMissing(self, trackId, title, fileName):
        if not self.readOnly:
            stmt = update(Track.__table__) \
                .where(Track.id == trackId) \
                .values(fileName=None,
                        filePath=None,
                        fileSize=0,
                        lastUpdated=arrow.utcnow().datetime,
                        hash=None)
            self.conn.execute(stmt)
        self.logger.warn("x Marked Track Missing [" + title + "]: File [" + fileName + "] Not Found.")

    @staticmethod
    def _makeTrackHash(artistId, id3String):
        return hashlib.md5((str(artistId) + str(id3String)).encode('utf-8')).hexdigest()

    def scan(self, folder, artist, release):
        """
        Scan the given folder and update, insert or delete track information
        :param folder: str
        :param artist: Artist
        :param release: Release
        :return:
        """
        if self.readOnly:
            self.logger.debug("[Read Only] Would Process Folder [" + folder + "] With Artist [" + str(artist) + "]")
            return None
        if not artist:
            raise RuntimeError("Invalid Artist")
        if not release:
            raise RuntimeError("Invalid Release")
        if not folder:
            raise RuntimeError("Invalid Folder")
        foundGoodMp3s = False
        startTime = arrow.utcnow().datetime
        self.logger.info("-> Scanning Folder [" + folder + "]")
        # Get any existing tracks for folder and verify; update if ID3 tags are different or delete if not found
        if not self.readOnly:
            for track in self.dbSession.query(Track).filter(Track.filePath == folder).all():
                filename = track.fullPath()
                # File no longer exists for track
                if not os.path.isfile(filename):
                    if not self.readOnly:
                        self._markTrackMissing(track.id, track.title, filename)
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
                            self._markTrackMissing(track.id, track.title, filename)
                    else:
                        try:
                            id3Hash = self._makeTrackHash(artist.roadieId, str(id3))
                            if id3Hash != track.Hash:
                                if not self.readOnly:
                                    self.logger.warn("x Hash Mismattch [" + track.Title + "]")
                                    self._markTrackMissing(track.id, track.title, filename)
                        except:
                            pass

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
                    foundGoodMp3s = True
                    head, tail = os.path.split(mp3)
                    headNoLibrary = head.replace(self.config['ROADIE_LIBRARY_FOLDER'], "")
                    trackHash = self._makeTrackHash(artist.roadieId, str(id3))
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
                                if isEqual(releaseTrack.trackNumber, id3.track) or isEqual(releaseTrack.hash, trackHash):
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
                        createdReleaseTracks += 1
                        self.dbSession.query(Track).filter(Track.hash == trackHash).delete(synchronize_session=False)
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
                        track.tags = []
                        track.partTitles = []
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
                            trackFullPath = os.path.join(self.libraryFolder, track.fullPath())
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
        matches = releaseMediaTrackCount == (createdReleaseTracks + foundReleaseTracks)
        if matches:
            release.libraryStatus = 'Complete'
        elif scannedMp3Files == 0:
            release.libraryStatus = 'Missing'
        else:
            release.libraryStatus = 'Incomplete'

        self.logger.info("<- Scanning Folder [" + str(folder.encode('utf-8')) + "] " +
                         "Complete, Scanned [" + ('%02d' % scannedMp3Files) + "] " +
                         "Mp3 Files: Created [" + str(createdReleaseTracks) + "] Release Tracks, " +
                         "Found [" + str(foundReleaseTracks) + "] Release Tracks. " +
                         "Sane Counts [" + str(matches) + "] " +
                         "Elapsed Time [" + str(elapsedTime) + "]")
        return foundGoodMp3s
