import os
import string

from goldfinch import validFileName as vfn

from resources.pathInfo import PathInfo


class ProcessorBase(object):
    libraryFolder = None
    config = None

    @staticmethod
    def allDirectoriesInDirectory(directory, isReleaseFolder=False):
        if isReleaseFolder:
            yield directory
        for root, dirs, files in os.walk(directory):
            if not dirs:
                yield root
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

    def artistFolder(self, artist):
        if not self.libraryFolder:
            self.libraryFolder = self.config['ROADIE_LIBRARY_FOLDER']
        artistFolder = artist.sortName or artist.name
        return os.path.join(self.libraryFolder, self.makeFileFriendly(artistFolder))

    def albumFolder(self, artist, year, albumTitle):
        return os.path.join(self.artistFolder(artist),
                            "[" + year.zfill(4)[:4] + "] " + self.makeFileFriendly(albumTitle))

    def trackName(self, trackNumber, trackTitle):
        return str(trackNumber).zfill(2) + " " + self.makeFileFriendly(trackTitle) + ".mp3"

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
