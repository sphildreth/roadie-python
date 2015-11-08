import os
import string

from goldfinch import validFileName as vfn

from resources.pathInfo import PathInfo


class ProcessorBase(object):
    def __init__(self, config):
        self.config = config
        self.libraryFolder = config['ROADIE_LIBRARY_FOLDER']
        if 'ROADIE_TRACK_PATH_REPLACE' in config:
            self.trackPathReplace = config['ROADIE_TRACK_PATH_REPLACE']

    def artistFolder(self, artist):
        result = artist.sortName or artist.name
        return os.path.join(self.libraryFolder, ProcessorBase.makeFileFriendly(result))

    def albumFolder(self, artist, year, albumTitle):
        return os.path.join(self.artistFolder(artist),
                            "[" + year.zfill(4)[:4] + "] " + ProcessorBase.makeFileFriendly(albumTitle))

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
