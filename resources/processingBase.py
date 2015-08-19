import os
import string
import json

from goldfinch import validFileName as vfn


class ProcessorBase(object):

    trackPathReplace = None

    def getConfig(self):
        d = os.path.dirname(os.path.realpath(__file__)).split(os.sep)
        path = os.path.join(os.sep.join(d[:-1]), "settings.json")
        with open(path, "r") as rf:
            return json.load(rf)

    def getTrackPathReplace(self):
        config = self.getConfig()
        if 'ROADIE_TRACK_PATH_REPLACE' in config:
            return config['ROADIE_TRACK_PATH_REPLACE']
        return []

    def fixPath(self, path):
        if not self.trackPathReplace:
            self.trackPathReplace = self.getTrackPathReplace()
        if self.trackPathReplace:
            for rpl in self.trackPathReplace:
                for key, val in rpl.items():
                    path = path.replace(key, val)
        return path

    def allDirectoriesInDirectory(self, directory):
        for root, dirs, files in os.walk(directory):
            if not dirs:
                yield root
            for dir in dirs:
                yield os.path.join(root, dir)

    def folderMp3Files(self, folder):
        for root, dirs, files in os.walk(folder):
            for filename in files:
                if os.path.splitext(filename)[1].lower() == ".mp3":
                    yield root, os.path.join(root, filename)

    def makeFileFriendly(self, input):
        return vfn(string.capwords(input), space="keep").decode('utf-8')

    def artistFolder(self, artist):
        artistFolder = artist.SortName or artist.Name
        config = self.getConfig()
        return self.fixPath(os.path.join(config['ROADIE_LIBRARY_FOLDER'], self.makeFileFriendly(artistFolder)))

    def albumFolder(self, artist, year, albumTitle):
        return self.fixPath(os.path.join(self.artistFolder(artist),
                            "[" + year.zfill(4)[:4] + "] " + self.makeFileFriendly(albumTitle)))

    def trackName(self, trackNumber, trackTitle):
        return str(trackNumber).zfill(2) + " " + self.makeFileFriendly(trackTitle) + ".mp3"