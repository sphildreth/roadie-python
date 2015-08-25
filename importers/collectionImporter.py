import re
import arrow
import csv
import linecache
import io
import os
import random
import shutil
import json
import hashlib
from PIL import Image
from dateutil.parser import *
from shutil import move
from mongoengine import connect
from resources.models import Artist, ArtistType, Collection, CollectionRelease, Label, Release, ReleaseLabel, Track, TrackRelease
from resources.musicBrainz import MusicBrainz
from resources.id3 import ID3
from resources.scanner import Scanner
from resources.convertor import Convertor
from resources.logger import Logger
from resources.processingBase import ProcessorBase

class CollectionImporter(ProcessorBase):

    def __init__(self, collectionId, readOnly, format, filename):
        self.logger = Logger()
        config = self.getConfig()
        self.collectionId = collectionId
        self.dbName = config['MONGODB_SETTINGS']['DB']
        self.host = config['MONGODB_SETTINGS']['host']
        self.readOnly = readOnly
        self.format = format
        self.positions = self.format.split(',')
        self._findColumns()
        if filename:
            self.filename = filename
            self._import()


    def _findColumns(self):
        self.position = -1
        self.release = -1
        self.artist = -1
        for i, position in enumerate(self.positions):
            if position.lower() == "position":
                self.position = i
            elif position.lower() == "release":
                self.release = i
            elif position.lower() == "artist":
                self.artist = i
        if self.position < 0 or self.release < 0 or self.artist < 0:
            self.logger.critical("Unable To Find Required Positions")
            return False
        return True


    def _import(self):
        if not os.path.exists(self.filename):
            self.logger.critical("Unable to Find CSV File [" + self.filename + "]")
        else:
            self.logger.debug("Importing [" + self.filename + "]")
            return self.importCsvData(open(self.filename))


    def importCsvData(self, csvData):
        connect(self.dbName, host=self.host)
        col = Collection.objects(id=self.collectionId).first()
        if not col:
            self.logger.critical("Unable to Find Collection Id [" + self.collectionId + "]")
            return False
        reader = csv.reader(csvData)
        col.Releases = []
        for row in reader:
            csvPosition = int(row[self.position].strip())
            csvArtist = row[self.artist].strip()
            csvRelease = row[self.release].strip()
            artist = Artist.objects(Name__iexact=csvArtist).first()
            if not artist:
                artist = Artist.objects(AlternateNames__iexact=csvArtist).first()
                if not artist:
                    artist = Artist.objects(__raw__= {'$or' : [
                        { 'Name' : { '$regex' : csvRelease, '$options': 'mi' }},
                        { 'AlternateNames' : { '$regex' : csvRelease, '$options': 'mi' }},
                    ]}).first()
                    if not artist:
                        self.logger.warn(("Not able to find Artist [" + csvArtist + "]").encode('utf-8'))
                        continue
            release = Release.objects(Title__iexact=csvRelease, Artist=artist).first()
            if not release:
                release = Release.objects(AlternateNames__iexact=csvRelease, Artist=artist).first()
                if not release:
                    release = Release.objects(__raw__= {'$or' : [
                        { 'Title' : { '$regex' : csvRelease, '$options': 'mi' }},
                        { 'AlternateNames' : { '$regex' : csvRelease, '$options': 'mi' }},
                    ]}).filter(Artist=artist).first()
                    if not release:
                        self.logger.warn(("Not able to find Release [" + csvRelease + "], Artist [" + csvArtist + "]").encode('utf-8'))
                        continue
            colRelease = CollectionRelease(Release=release, ListNumber=csvPosition)
            col.Releases.append(colRelease)
            self.logger.info("Added Position [" + str(csvPosition) + "] Release [" + str(release)+ "] To Collection")
        col.LastUpdated = arrow.utcnow().datetime
        Collection.save(col)
        return True