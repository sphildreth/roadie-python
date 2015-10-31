import os
import json
import hashlib
import random
import uuid
import arrow

from sqlalchemy.sql import func, and_, or_, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, update

from resources.common import *
from resources.models.Artist import Artist
from resources.models.Genre import Genre
from resources.models.Image import Image
from resources.models.Label import Label
from resources.models.Release import Release
from resources.models.ReleaseLabel import ReleaseLabel
from resources.models.ReleaseMedia import ReleaseMedia
from resources.models.Track import Track

from factories.artistFactory import ArtistFactory
from factories.releaseFactory import ReleaseFactory

from resources.id3 import ID3
from resources.logger import Logger
from resources.processingBase import ProcessorBase


class Validator(ProcessorBase):
    def __init__(self, config, dbConn, dbSession, readOnly):
        self.config = config
        self.readOnly = readOnly or False
        self.logger = Logger()
        self.conn = dbConn
        self.session = dbSession

    def validateArtists(self):
        for artist in self.session.query(Artist).all():
            self.validate(artist)

    def validate(self, artist):
        """
        Do sanity checks on given Artist
        :param artist: Artist
        :return:
        """
        if not artist:
            raise RuntimeError("Invalid Artist")
        for release in artist.releases:
            self.logger.info("Validating Artist [" + str(artist) + "], Release [" + str(release) + "]")
            releaseFolder = self.albumFolder(artist, release.ReleaseDate[:4], release.Title)
            if not os.path.exists(releaseFolder):
                if not self.readOnly:
                    self.session.delete(release)
                self.logger.warn("X Deleting Release [" + str(release) + "] Folder [" + releaseFolder + "] Not Found")
                continue
            goodTracks = []
            for releaseMedia in release.media:
                for track in releaseMedia:
                    try:
                        trackFilename = self.fixPath(os.path.join(track.Track.FilePath, track.Track.FileName))
                        if not os.path.exists(trackFilename):
                            if not self.readOnly:
                                self.session.delete(track)
                            self.logger.warn("X Deleting Track [" + str(track.Track) + "] File [" + trackFilename + "] not found")
                        elif track not in goodTracks:
                            goodTracks.append(track)
                    except:
                        pass
            if not self.readOnly:
                release.tracks = goodTracks
                release.lastUpdated = arrow.utcnow().datetime
        self.session.commit()

