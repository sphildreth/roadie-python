# Validator that looks at Artist folder and manipulates Database

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
from models import Artist, ArtistType, Label, Release, ReleaseLabel, Track, TrackRelease
from musicBrainz import MusicBrainz
from id3 import ID3
from scanner import Scanner
from convertor import Convertor
from resources.logger import Logger
from processor import Processor
from resources.processingBase import ProcessorBase

class Validator(ProcessorBase):

    def __init__(self, readOnly):
        d = os.path.dirname(os.path.realpath(__file__)).split(os.sep)
        path = os.path.join(os.sep.join(d[:-1]), "settings.json")
        with open(path, "r") as rf:
            config = json.load(rf)
        self.dbName = config['MONGODB_SETTINGS']['DB']
        self.host = config['MONGODB_SETTINGS']['host']
        self.readOnly = readOnly or False
        self.logger = Logger()

    def validate(self, artist):
        if not artist:
            raise RuntimeError("Invalid Artist")
        self.logger.info("Validating Artist [" + str(artist) + "]")
        connect(self.dbName, host=self.host)
        now = arrow.utcnow().datetime
        for release in Release.objects(Artist=artist):
            releaseFolder = self.albumFolder(artist, release.ReleaseDate[:4], release.Title)
            if not os.path.exists(releaseFolder):
                if not self.readOnly:
                    Release.delete(release)
                self.logger.warn("X Deleting Release [" + str(release) + "] Folder [" + releaseFolder + "] Not Found")
                continue
            newReleaseTracks = []
            for track in release.Tracks:
                trackFilename = os.path.join(track.Track.FilePath, track.Track.FileName);
                if not os.path.exists(trackFilename):
                    if not self.readOnly:
                        Track.delete(track.Track)
                    self.logger.warn("X Deleting Track [" + str(track.Track) + "] File [" + trackFilename + "] not found")
                else:
                    newReleaseTracks.append(track)
            if newReleaseTracks and (len(newReleaseTracks) != len(release.Tracks)):
                release.Tracks = newReleaseTracks
                release.LastUpdated = now
                if not self.readOnly:
                    Release.save(release)
                self.logger.info("Updated Release [" + str(release) + "] Tracks")
