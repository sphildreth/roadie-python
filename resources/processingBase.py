import arrow
import linecache
import io
import os
import random
import sys
import shutil
import json
import hashlib
import argparse
from PIL import Image
from dateutil.parser import *
from goldfinch import validFileName as vfn
from shutil import move
from mongoengine import connect
from resources.models import Artist, ArtistType, Label, Release, ReleaseLabel, Track, TrackRelease
from resources.musicBrainz import MusicBrainz
from resources.id3 import ID3
from resources.scanner import Scanner
from resources.convertor import Convertor
from resources.logger import Logger


class ProcessorBase(object):

    def getConfig(self):
        d = os.path.dirname(os.path.realpath(__file__)).split(os.sep)
        path = os.path.join(os.sep.join(d[:-1]), "settings.json")
        with open(path, "r") as rf:
            return json.load(rf)

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

    def makeFileFriendly(self, string):
        return vfn(string.title(), space="keep").decode('utf-8')

    def artistFolder(self, artist):
        artistFolder = artist.SortName or artist.Name
        config = self.getConfig()
        return os.path.join(config['ROADIE_LIBRARY_FOLDER'], self.makeFileFriendly(artistFolder))

    def albumFolder(self, artist, year, albumTitle):
        return os.path.join(self.artistFolder(artist),
                            "[" + year.zfill(4)[:4] + "] " + self.makeFileFriendly(albumTitle))

    def trackName(self, trackNumber, trackTitle):
        return str(trackNumber).zfill(2) + " " + self.makeFileFriendly(trackTitle) + ".mp3"