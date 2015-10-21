import io
import os
import random
import shutil
import string

import hashlib
from shutil import move

import arrow
from PIL import Image
# from dateutil.parser import *
from mongoengine import connect

from resources.common import *
from resources.pathInfo import PathInfo
from resources.models.Artist import Artist
from resources.models.Genre import Genre
from resources.models.Label import Label
from resources.models.Release import Release
from resources.models.ReleaseLabel import ReleaseLabel
from resources.models.ReleaseMedia import ReleaseMedia
from resources.models.Track import Track, TrackStatus

from factories.artistFactory import ArtistFactory
from factories.releaseFactory import ReleaseFactory

from resources.id3 import ID3
from resources.scanner import Scanner
from resources.convertor import Convertor
from resources.logger import Logger
from resources.processingBase import ProcessorBase


class Processor(ProcessorBase):
    def __init__(self, config, dbConn, dbSession, readOnly, dontDeleteInboundFolders):
        self.config = config
        self.InboundFolder = self.config['ROADIE_INBOUND_FOLDER']
        self.LibraryFolder = self.config['ROADIE_LIBRARY_FOLDER']
        # TODO if set then process music files; like clear comments
        self.processingOptions = self.config['ROADIE_PROCESSING']
        self.conn = dbConn
        self.session = dbSession
        self.logger = Logger()
        self.thumbnailSize = self.config['ROADIE_THUMBNAILS']['Height'], self.config['ROADIE_THUMBNAILS']['Width']
        self.readOnly = readOnly or False
        self.dontDeleteInboundFolders = dontDeleteInboundFolders or False
        self.artistFactory = ArtistFactory(dbConn, dbSession)
        self.releaseFactory = ReleaseFactory(dbConn, dbSession)

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
    def shouldMoveToLibrary(self, artist, artistId, id3, mp3):
        try:
            fileFolderLibPath = self.albumFolder(artist, id3.year, id3.album)
            os.makedirs(fileFolderLibPath, exist_ok=True)
            fullFileLibPath = os.path.join(fileFolderLibPath,
                                           self.makeFileFriendly(self.trackName(id3.track, id3.title)))
            if not os.path.isfile(fullFileLibPath):
                # Does not exist copy it over
                return True
            else:
                # Does exist see if the one being copied is 'better' then the existing
                existingId3 = ID3(fullFileLibPath, self.processingOptions)
                if not existingId3.isValid():
                    return True
                existingId3Hash = hashlib.md5((str(artistId) + str(existingId3)).encode('utf-8')).hexdigest()
                id3Hash = hashlib.md5(str(id3).encode('utf-8')).hexdigest()
                if existingId3Hash == id3Hash:
                    # If the hashes are equal its Likely the same file
                    return False
                # If The existing is longer or has a high bitrate then use existing
                if existingId3.length > id3.length and existingId3.bitrate > id3.bitrate:
                    return False
            return True
        except:
            self.logger.exception()
            return False

    def readImageThumbnailBytesFromFile(self, path):
        try:
            img = Image.open(path).convert('RGB')
            img.thumbnail(self.thumbnailSize)
            b = io.BytesIO()
            img.save(b, "JPEG")
            return b.getvalue()
        except:
            return None

    # If should be moved then move over and return new filename
    def moveToLibrary(self, artist, id3, mp3):
        try:
            newFilename = os.path.join(self.artistFolder(artist), self.albumFolder(artist, id3.year, id3.album),
                                       self.trackName(id3.track, id3.title))
            isMp3File = os.path.isfile(mp3)
            isNewFilenameFile = os.path.isfile(newFilename)
            # If it already exists delete it as the shouldMove function determines if
            # the file should be overwritten or not
            if isMp3File and isNewFilenameFile and not os.path.samefile(mp3, newFilename):
                try:
                    os.remove(newFilename)
                    self.logger.warn("x Deleting Existing [" + newFilename + "]")
                except OSError:
                    pass

            if isMp3File and isNewFilenameFile and not os.path.samefile(mp3, newFilename):
                try:
                    move(mp3, newFilename)
                    self.logger.info("= Moving [" + mp3 + "] => [" + newFilename + "]")
                except OSError:
                    pass

            return newFilename
        except:
            self.logger.exception()
            return None

    def process(self, **kwargs):
        """
        Process folder using the passed folder

        """
        inboundFolder = kwargs.pop('folder', self.InboundFolder)
        self.logger.info("Processing Folder [" + inboundFolder + "]")
        scanner = Scanner(self.config, self.conn, self.session, self.readOnly)
        startTime = arrow.utcnow().datetime
        newMp3Folder = None
        lastID3Artist = None
        lastID3Album = None
        artist = None
        release = None
        mp3FoldersProcessed = []
        # Get all the folder in the InboundFolder
        for mp3Folder in self.allDirectoriesInDirectory(inboundFolder):
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
            for rootFolder, mp3 in self.folderMp3Files(mp3Folder):
                if mp3Folder not in mp3FoldersProcessed:
                    mp3FoldersProcessed.append(mp3Folder)
                    pathInfo = self.infoFromPath(os.path.basename(mp3))
                    self.logger.debug("Processing MP3 PathInfo [" + str(pathInfo) + "] File [" + mp3 + "]...")
                    id3 = ID3(mp3, self.processingOptions)
                    if id3 is not None:
                        self.logger.debug("ID3 Info [" + id3.info() + "]")
                        if not id3.isValid():
                            self.logger.warn("! Track Has Invalid or Missing ID3 Tags [" + mp3 + "]")
                        else:
                            foundMp3Files += 1
                            # Get Artist
                            if lastID3Artist != id3.artist:
                                artist = None
                            if not artist:
                                lastID3Artist = id3.artist
                                artist = self.artistFactory.get(id3.artist)
                            if artist and artist.isLocked:
                                self.logger.debug(
                                    "Skipping Processing Track [" + mp3 + "], Artist [" + str(artist) + "] Is Locked")
                                continue
                            # Get the Release
                            if lastID3Album != id3.album:
                                release = None
                            if not release:
                                lastID3Album = id3.album
                                release = self.releaseFactory.get(artist, id3.album)
                                if not release:
                                    # Was not found in any Searcher create and add
                                    release = self.releaseFactory.create(artist,
                                                                         string.capwords(id3.album),
                                                                         1,
                                                                         id3.year)
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
                                        release.status = TrackStatus.ProcessorAdded
                                        self.releaseFactory.add(release)
                                        self.logger.info("+ Processor Added Release [" + str(release.info()) + "]")
                            if self.shouldMoveToLibrary(artist, artist.id, id3, mp3):
                                newMp3 = self.moveToLibrary(artist, id3, mp3)
                                head, tail = os.path.split(newMp3)
                                newMp3Folder = head
            if artist and release:
                if newMp3Folder and newMp3Folder not in mp3FoldersProcessed:
                    for coverImage in self.releaseCoverImages(mp3Folder):
                        try:
                            im = Image.open(coverImage).convert('RGB')
                            newPath = os.path.join(newMp3Folder, "cover.jpg")
                            if (not os.path.isfile(newPath) or not os.path.samefile(coverImage, newPath)) and not self.readOnly:
                                im.save(newPath)
                                self.logger.info("+ Copied Cover File [" + coverImage + "] => [" + newPath + "]")
                        except:
                            self.logger.exception("Error Copying File [" + coverImage + "]")
                            pass
                    scanner.scan(newMp3Folder, artist, release)
                    mp3FoldersProcessed.append(newMp3Folder)
                elif mp3Folder not in mp3FoldersProcessed:
                    scanner.scan(mp3Folder, artist, release)
                    mp3FoldersProcessed.append(mp3Folder)

            if not self.readOnly and artist and release:
                if self.shouldDeleteFolder(mp3Folder):
                    try:
                        shutil.rmtree(mp3Folder)
                        self.logger.debug("x Deleted Processed Folder [" + mp3Folder + "]")
                    except OSError:
                        pass
        elapsedTime = arrow.utcnow().datetime - startTime
        self.session.commit()
        self.logger.debug("-> MP3 Folders Processed [" + ",".join([x for x in mp3FoldersProcessed]) + "]")
        self.logger.info("Processing Complete. Elapsed Time [" + str(elapsedTime) + "]")
