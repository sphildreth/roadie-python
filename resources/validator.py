# Validator that looks at Artist folder and manipulates Database

import os
import json

import arrow

from mongoengine import connect

from resources.models import Release, Track
from resources.logger import Logger
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
        connect(self.dbName, host=self.host)
        for release in Release.objects(Artist=artist):
            self.logger.info("Validating Artist [" + str(artist) + "], Release [" + str(release) + "]")
            releaseFolder = self.albumFolder(artist, release.ReleaseDate[:4], release.Title)
            if not os.path.exists(releaseFolder):
                if not self.readOnly:
                    Release.delete(release)
                self.logger.warn("X Deleting Release [" + str(release) + "] Folder [" + releaseFolder + "] Not Found")
                continue
            goodTracks = []
            for track in release.Tracks:
                try:
                    trackFilename = self.fixPath(os.path.join(track.Track.FilePath, track.Track.FileName))
                    if not os.path.exists(trackFilename):
                        if not self.readOnly:
                            Release.objects(Artist=track.Artist).update_one(pull__Tracks__Track=track)
                            Track.delete(track.Track)
                        self.logger.warn("X Deleting Track [" + str(track.Track) + "] File [" + trackFilename + "] not found")
                    elif track not in goodTracks:
                        self.logger.info("Adding Track [" + str(track.Track) + '] Hash [' + str(track.Hash) + '] to Release')
                        goodTracks.append(track)
                except:
                    pass
            if not self.readOnly:
                release.Tracks = goodTracks
                release.LastUpdated = arrow.utcnow().datetime
                Release.save(release)


