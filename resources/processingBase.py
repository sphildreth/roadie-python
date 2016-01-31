import os
import string
import hashlib

from shutil import move
from goldfinch import validFileName as vfn

from resources.id3 import ID3
from resources.pathInfo import PathInfo
from resources.common import *
from resources.logger import Logger


class ProcessorBase(object):
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger or Logger()
        self.libraryFolder = config['ROADIE_LIBRARY_FOLDER']
        self.trackPathReplace = None
        if 'ROADIE_TRACK_PATH_REPLACE' in config:
            self.trackPathReplace = config['ROADIE_TRACK_PATH_REPLACE']

    @staticmethod
    def makeTrackHash(artistId, id3String):
        return hashlib.md5((str(artistId) + str(id3String)).encode('utf-8')).hexdigest()

    def artistFolder(self, artist):
        result = artist.sortName or artist.name
        return os.path.join(self.libraryFolder, ProcessorBase.makeFileFriendly(result))

    def albumFolder(self, artist, year, albumTitle):
        return os.path.join(self.artistFolder(artist),
                            "[" + year.zfill(4)[:4] + "] " + ProcessorBase.makeFileFriendly(albumTitle))

    def tryToFindFileForTrack(self, artist, track):
        """
        Try to find given track in artists folder. This is useful is the track is not where expected based on album tag info
        :param artist: Artist
        :param track: Track
        """
        try:
            for folder in self.allDirectoriesInDirectory(self.artistFolder(artist), False):
                for rootFolder, mp3 in ProcessorBase.folderMp3Files(folder):
                    mp3Id3 = ID3(mp3, self.config)
                    if mp3Id3 is not None:
                        if isEqual(mp3Id3.title, track.title) and isEqual(mp3Id3.track, track.trackNumber):
                            return {
                                'folderName': folder,
                                'fileName': mp3,
                                'id3': mp3Id3
                            }
        except:
            pass
        return None

    def moveToLibrary(self, artist, id3, mp3):
        """
        If should be moved then move over and return new filename
        :param artist: Artist
        :param id3: ID3
        :param mp3: str
        :return:
        """
        try:
            albumFolder = os.path.join(self.artistFolder(artist), self.albumFolder(artist, id3.year, id3.album))
            newFilename = os.path.join(albumFolder,
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
                    self.logger.exception("Error Moving Track")
                    pass

            isNewFilenameFile = os.path.isfile(newFilename)
            if isMp3File:
                if (isNewFilenameFile and not os.path.samefile(mp3, newFilename)) or not isNewFilenameFile:
                    try:
                        if not os.path.exists(albumFolder):
                            os.makedirs(albumFolder)
                        self.logger.info("= Moving [" + mp3 + "] => [" + newFilename + "]")
                        move(mp3, newFilename)
                    except OSError:
                        self.logger.exception("Error Moving Track")
                        newFilename = None
                        pass

            return newFilename
        except:
            self.logger.exception()
            return None

    def pathToTrack(self, track):
        """
        Adjust the path to a track with any OS or config substitutions like mapped drive to storage path change
        :param track: Track
        :return: str
        """
        if not track or not track.filePath or not track.fileName:
            return None
        path = os.path.join(self.libraryFolder, track.filePath, track.fileName)
        if self.trackPathReplace:
            for rpl in self.trackPathReplace:
                for key, val in rpl.items():
                    path = path.replace(key, val)
        return path

    @staticmethod
    def trackName(trackNumber, trackTitle):
        return str(trackNumber).zfill(2) + " " + ProcessorBase.makeFileFriendly(trackTitle) + ".mp3"

    @staticmethod
    def allDirectoriesInDirectory(directory, isReleaseFolder=False):
        if isReleaseFolder:
            yield directory
        for root, dirs, files in os.walk(directory):
            for d in dirs:
                yield os.path.join(root, d)

    @staticmethod
    def folderMp3Files(folder):
        for root, dirs, files in os.walk(folder):
            for filename in files:
                if os.path.splitext(filename)[1].lower() == ".mp3":
                    yield root, os.path.join(root, filename)

    @staticmethod
    def makeFileFriendly(fileName):
        return vfn(string.capwords(fileName), space="keep").decode('utf-8')

    @staticmethod
    def infoFromPath(filePath):
        """
        See if given path is in "<Artist> -- [Year] <ReleaseTitle>" format is so then return parsed info
        :param filePath: str
                         Path To Parse
        :return: PathInfo
        """
        if not filePath:
            return None
        parts = filePath.split("--")
        if parts and len(parts) == 2:
            artistName = string.capwords(parts[0])
            secondPart = parts[1].strip()
            releaseYear = secondPart[1:4]
            releaseTitle = string.capwords(secondPart[4:])
            return PathInfo(artistName, releaseYear, releaseTitle)
