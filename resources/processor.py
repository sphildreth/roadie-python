import io
import hashlib
import os
import random
import shutil
import string
import sqlite3
import hashlib
from shutil import move
import arrow
from PIL import Image
import gc
from resources.common import *
from resources.pathInfo import PathInfo
from resources.models.Artist import Artist
from resources.models.Genre import Genre
from resources.models.Label import Label
from resources.models.Release import Release
from resources.models.ReleaseLabel import ReleaseLabel
from resources.models.ReleaseMedia import ReleaseMedia
from resources.models.Track import Track
from factories.artistFactory import ArtistFactory
from factories.releaseFactory import ReleaseFactory
from resources.id3 import ID3
from resources.scanner import Scanner
from resources.convertor import Convertor
from resources.logger import Logger
from resources.processingBase import ProcessorBase
from resources.validator import Validator


class Processor(ProcessorBase):
    def __init__(self, config, dbConn, dbSession, readOnly, dontDeleteInboundFolders, flushBefore=False):
        self.config = config
        self.InboundFolder = self.config['ROADIE_INBOUND_FOLDER']
        # TODO if set then process music files; like clear comments
        self.processingOptions = self.config['ROADIE_PROCESSING']
        self.conn = dbConn
        self.session = dbSession
        self.logger = Logger()
        self.thumbnailSize = self.config['ROADIE_THUMBNAILS']['Height'], self.config['ROADIE_THUMBNAILS']['Width']
        self.readOnly = readOnly or False
        self.dontDeleteInboundFolders = dontDeleteInboundFolders or False
        self.flushBefore = flushBefore
        self.artistFactory = ArtistFactory(dbConn, dbSession)
        self.releaseFactory = ReleaseFactory(dbConn, dbSession)
        self.folderDB = sqlite3.connect("processorFolder.db")
        self.folderDB.execute("CREATE TABLE IF NOT EXISTS `folder` (namehash text, mtime real);")
        self.folderDB.execute("CREATE INDEX IF NOT EXISTS `idx_folder_namehash` on `folder`(namehash);")
        self.folderDB.commit()
        super().__init__(config)

    def _doProcessFolder(self, name, mtime, forceFolderScan):
        try:
            nameHash = hashlib.md5(name.encode('utf-8')).hexdigest()
            folderDbRecord = self.folderDB.execute(
                "SELECT * FROM `folder` WHERE namehash='" + nameHash + "';").fetchone()
            if not folderDbRecord:
                self.folderDB.execute("INSERT INTO `folder` VALUES ('" + nameHash + "', " + str(mtime) + ");")
                self.folderDB.commit()
                return True
            if forceFolderScan:
                if folderDbRecord:
                    self.folderDB.execute(
                        "UPDATE `folder` SET mtime = " + str(mtime) + " WHERE namehash = '" + nameHash + "';")
                else:
                    self.folderDB.execute("INSERT INTO `folder` VALUES ('" + nameHash + "', " + str(mtime) + ");")
                self.folderDB.commit()
                return True
            return folderDbRecord[1] != mtime
        except:
            return True

    def releaseCoverImages(self, folder):
        try:
            image_filter = ['.jpg', '.jpeg', '.bmp', '.png', '.gif']
            cover_filter = ['cover', 'front']
            for r, d, f in os.walk(folder):
                for file in f:
                    root, file = os.path.split(file)
                    root, ext = os.path.splitext(file)
                    if ext.lower() in image_filter and root.lower() in cover_filter:
                        yield os.path.join(r, file)
        except:
            self.logger.exception()

    def shouldDeleteFolder(self, mp3Folder):
        if self.dontDeleteInboundFolders:
            return False

        if self.readOnly:
            return False

        # Is folder to delete empty?
        if not os.listdir(mp3Folder):
            return True

        return False

    # Determine if the found file should be moved into the library; check for existing and see if better
    def shouldMoveToLibrary(self, artist, id3, mp3):
        try:
            fileFolderLibPath = self.albumFolder(artist, id3.year, id3.album)
            os.makedirs(fileFolderLibPath, exist_ok=True)
            fullFileLibPath = os.path.join(fileFolderLibPath,
                                           ProcessorBase.makeFileFriendly(ProcessorBase.trackName(id3.track, id3.title)))
            if not os.path.isfile(fullFileLibPath):
                # Does not exist copy it over
                return True
            else:
                # Does exist see if the one being copied is 'better' then the existing
                existingId3 = ID3(fullFileLibPath, self.processingOptions)
                if not existingId3.isValid():
                    return True
                existingId3Hash = hashlib.md5((str(artist.roadieId) + str(existingId3)).encode('utf-8')).hexdigest()
                id3Hash = hashlib.md5((str(artist.roadieId) + str(id3)).encode('utf-8')).hexdigest()
                if existingId3Hash == id3Hash:
                    # If the hashes are equal its Likely the same file
                    return False
                # If The existing is longer or has a higher bitrate then use existing
                if existingId3.length > id3.length and existingId3.bitrate > id3.bitrate:
                    return False
            return True
        except:
            self.logger.exception("shouldMoveToLibrary: Id3 [" + str(id3) + "]")
            return False

    def moveToLibrary(self, artist, id3, mp3):
        """
        If should be moved then move over and return new filename
        :param artist: Artist
        :param id3: ID3
        :param mp3: str
        :return:
        """
        try:
            newFilename = os.path.join(self.artistFolder(artist), self.albumFolder(artist, id3.year, id3.album),
                                       ProcessorBase.trackName(id3.track, id3.title))
            isMp3File = os.path.isfile(mp3)
            isNewFilenameFile = os.path.isfile(newFilename)
            # If it already exists delete it as the shouldMove function determines if
            # the file should be overwritten or not
            if isMp3File and isNewFilenameFile and not os.path.samefile(mp3, newFilename):
                try:
                    self.logger.warn("x Deleting Existing [" + newFilename + "]")
                    os.remove(newFilename)
                except OSError:
                    pass

            isNewFilenameFile = os.path.isfile(newFilename)
            if isMp3File:
                if (isNewFilenameFile and not os.path.samefile(mp3, newFilename)) or not isNewFilenameFile:
                    try:
                        self.logger.info("= Moving [" + mp3 + "] => [" + newFilename + "]")
                        move(mp3, newFilename)
                    except OSError:
                        pass

            return newFilename
        except:
            self.logger.exception()
            return None

    def processArtists(self, dontValidate):
        """

        :param dontValidate: bool
        """
        validator = Validator(self.config, self.conn, self.session, False)
        for artist in self.session.query(Artist).filter(Artist.isLocked == 0).order_by(Artist.name):
            self.logger.debug("=: Processing Artist [" + str(artist.name) + "] RoadieId [" + artist.roadieId + "]")
            self.process(folder=self.artistFolder(artist), forceFolderScan=True)
            if not dontValidate:
                validator.validate(artist)

    def process(self, **kwargs):
        """
        Process folder using the passed folder

        """
        try:
            inboundFolder = kwargs.pop('folder', self.InboundFolder)
            forceFolderScan = kwargs.pop('forceFolderScan', False)
            isReleaseFolder = kwargs.pop('isReleaseFolder', False)
            self.logger.info("Processing Folder [" + inboundFolder + "] Flush [" + str(self.flushBefore) + "]")
            scanner = Scanner(self.config, self.conn, self.session, self.artistFactory, self.readOnly)
            startTime = arrow.utcnow().datetime
            newMp3Folder = None
            lastID3Artist = None
            lastID3Album = None
            artist = None
            release = None
            mp3FoldersProcessed = []
            # Get all the folder in the InboundFolder
            for mp3Folder in ProcessorBase.allDirectoriesInDirectory(inboundFolder, isReleaseFolder):
                try:
                    mp3FolderMtime = max(os.path.getmtime(root) for root, _, _ in os.walk(mp3Folder))
                    if not self._doProcessFolder(mp3Folder, mp3FolderMtime, forceFolderScan):
                        self.logger.info("Skipping Folder [" + mp3Folder + "] No Changes Detected")
                        continue

                    foundMp3Files = 0

                    # Do any conversions
                    if not self.readOnly:
                        Convertor(mp3Folder)

                    # Delete any empty folder if enabled
                    if not os.listdir(mp3Folder) and not self.dontDeleteInboundFolders:
                        try:
                            self.logger.warn("X Deleted Empty Folder [" + mp3Folder + "]")
                            if not self.readOnly:
                                os.rmdir(mp3Folder)
                        except OSError:
                            self.logger.error("Error Deleting [" + mp3Folder + "]")
                        continue

                    # Get all the MP3 files in the Folder and process
                    for rootFolder, mp3 in ProcessorBase.folderMp3Files(mp3Folder):
                        printableMp3 = mp3.encode('ascii', 'ignore').decode('utf-8')
                        self.logger.debug("Processing MP3 File [" + printableMp3 + "]")
                        id3StartTime = arrow.utcnow().datetime
                        id3 = ID3(mp3, self.processingOptions)
                        id3ElapsedTime = arrow.utcnow().datetime - id3StartTime
                        if id3 is not None:
                            if not id3.isValid():
                                self.logger.warn("! Track Has Invalid or Missing ID3 Tags [" + printableMp3 + "]")
                            else:
                                foundMp3Files += 1
                                # Get Artist
                                if lastID3Artist != id3.getReleaseArtist():
                                    artist = None
                                if not artist:
                                    lastID3Artist = id3.getReleaseArtist()
                                    r = release
                                    if not r:
                                        r = Release()
                                        r.title = id3.album
                                        r.artist = Artist()
                                        r.artist.name = id3.getReleaseArtist()
                                    artist = self.artistFactory.get(id3.getReleaseArtist(), not r.isCastRecording())
                                if artist and artist.isLocked:
                                    self.logger.debug(
                                        "Skipping Processing Track [" + printableMp3 + "], Artist [" + str(
                                            artist) + "] Is Locked")
                                    continue
                                if self.flushBefore:
                                    if artist.isLocked:
                                        self.logger.debug(
                                            "Skipping Flushing Artist [" + printableMp3 + "], Artist [" + str(
                                                artist) + "] Is Locked")
                                        continue
                                    else:
                                        for release in artist.releases:
                                            release.genres = []
                                            self.session.delete(release)
                                        self.session.commit()
                                if not artist:
                                    self.logger.warn(
                                        "! Unable to Find Artist [" + id3.getReleaseArtist() + "] for Mp3 [" + printableMp3 + "]")
                                    continue
                                # Get the Release
                                if lastID3Album != id3.album:
                                    release = None
                                if not release:
                                    lastID3Album = id3.album
                                    release = self.releaseFactory.get(artist, id3.album)
                                    if release:
                                        # Was found now see if needs update based on id3 tag info
                                        id3ReleaseDate = parseDate(id3.year)
                                        if not release.releaseDate == id3ReleaseDate and id3ReleaseDate:
                                            release.releaseDate = id3ReleaseDate
                                        if id3.imageBytes and not release.thumbnail:
                                            try:
                                                img = Image.open(io.BytesIO(id3.imageBytes)).convert('RGB')
                                                img.thumbnail(self.thumbnailSize)
                                                b = io.BytesIO()
                                                img.save(b, "JPEG")
                                                release.thumbnail = b.getvalue()
                                            except:
                                                pass

                                    else:
                                        # Was not found in any Searcher create and add
                                        self.logger.debug("Release [" + id3.album + "] Not Found By Factory")
                                        release = self.releaseFactory.create(artist,
                                                                             string.capwords(id3.album),
                                                                             1,
                                                                             id3.year)
                                        if not release:
                                            self.logger.warn("! Unable to Create Album [" + id3.album +
                                                             "] For Track [" + printableMp3 + "]")
                                            continue
                                        if release:
                                            if id3.imageBytes:
                                                try:
                                                    img = Image.open(io.BytesIO(id3.imageBytes)).convert('RGB')
                                                    img.thumbnail(self.thumbnailSize)
                                                    b = io.BytesIO()
                                                    img.save(b, "JPEG")
                                                    release.thumbnail = b.getvalue()
                                                except:
                                                    pass
                                            release.status = 1
                                            self.releaseFactory.add(release)
                                            self.logger.info(
                                                "+ Processor Added Release [" + str(release.info()) + "]")
                                            self.session.commit()
                                if self.shouldMoveToLibrary(artist, id3, mp3):
                                    newMp3 = self.moveToLibrary(artist, id3, mp3)
                                    head, tail = os.path.split(newMp3)
                                    newMp3Folder = head
                    if artist and release:
                        if not release.releaseDate and release.media:
                            for media in release.media:
                                if media.tracks:
                                    for track in media.tracks:
                                        if track.filePath:
                                            release.releaseDate = parseDate(track.filePath.split('\\')[1][1:5])
                                            break
                                        else:
                                            continue
                                        break
                                    else:
                                        continue
                                    break
                            else:
                                continue
                            break
                        if not release.releaseDate:
                            release.releaseDate = parseDate(id3.year)
                        releaseFolder = self.albumFolder(artist, release.releaseDate.strftime('%Y'), release.title)
                        if newMp3Folder and newMp3Folder not in mp3FoldersProcessed:
                            for coverImage in self.releaseCoverImages(mp3Folder):
                                try:
                                    im = Image.open(coverImage).convert('RGB')
                                    newPath = os.path.join(newMp3Folder, "cover.jpg")
                                    if (not os.path.isfile(newPath) or not os.path.samefile(coverImage,
                                                                                            newPath)) and not self.readOnly:
                                        im.save(newPath)
                                        self.logger.info(
                                            "+ Copied Cover File [" + coverImage + "] => [" + newPath + "]")
                                except:
                                    self.logger.exception("Error Copying File [" + coverImage + "]")
                                    pass
                            mp3FoldersProcessed.append(newMp3Folder)
                    if not self.readOnly and artist and release:
                        if self.shouldDeleteFolder(mp3Folder):
                            try:
                                shutil.rmtree(mp3Folder)
                                self.logger.debug("x Deleted Processed Folder [" + mp3Folder + "]")
                            except OSError:
                                self.logger.warn("Could Not Delete Folder [" + mp3Folder + "]")
                                pass
                    self.session.commit()
                    gc.collect()

                except:
                    self.logger.exception("Processing Exception Occurred, Rolling Back Session Transactions")
                    self.session.rollback()
            scanner.scan(releaseFolder, artist, release)
            # Sync  the counts as some release media and release tracks where added by the processor
            release.mediaCount = len(release.media)
            for media in release.media:
                media.trackCount = len(media.tracks)
                release.trackCount = len(media.tracks)
            elapsedTime = arrow.utcnow().datetime - startTime
            self.session.commit()
            self.logger.info("Processing Complete. Elapsed Time [" + str(elapsedTime) + "]")
        except:
            self.logger.exception("Processing Exception Occurred, Rolling Back Session Transactions")
            self.session.rollback()
