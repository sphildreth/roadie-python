import csv
import os
import uuid
import arrow
from resources.logger import Logger
from resources.processingBase import ProcessorBase
from resources.models.Collection import Collection
from resources.models.CollectionRelease import CollectionRelease
from factories.artistFactory import ArtistFactory
from factories.releaseFactory import ReleaseFactory


class CollectionImporter(ProcessorBase):
    def __init__(self, dbConn, dbSession, collectionId, readOnly, format, filename):
        self.logger = Logger()
        self.dbConn = dbConn
        self.dbSession = dbSession
        self.collectionId = collectionId
        self.artistFactory = ArtistFactory(dbConn, dbSession)
        self.releaseFactory = ReleaseFactory(dbConn, dbSession)
        self.notFoundEntryInfo = []
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
            elif position.lower() == "release" or position.lower() == "album":
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
        col = self.dbSession.query(Collection).filter(Collection.id == self.collectionId).first()
        if not col:
            self.logger.critical("Unable to Find Collection Id [" + self.collectionId + "]")
            return False
        reader = csv.reader(csvData)
        col.collectionReleases = []
        for row in reader:
            csvPosition = int(row[self.position].strip())
            csvArtist = row[self.artist].strip()
            csvRelease = row[self.release].strip()
            artist = self.artistFactory.get(csvArtist, False)
            if not artist:
                self.logger.warn(("Artist [" + csvArtist + "] Not Found In Database").encode('utf-8'))
                self.notFoundEntryInfo.append({'position': csvPosition, 'artist': csvArtist, 'release': csvRelease});
                continue
            release = self.releaseFactory.get(artist, csvRelease, False)
            if not release:
                self.logger.warn(
                    ("Not able to find Release [" + csvRelease + "], Artist [" + csvArtist + "]").encode(
                        'utf-8'))
                self.notFoundEntryInfo.append({'position': csvPosition, 'artist': csvArtist, 'release': csvRelease});
                continue
            colRelease = CollectionRelease()
            colRelease.releaseId = release.id
            colRelease.listNumber = csvPosition
            colRelease.createdDate = arrow.utcnow().datetime
            colRelease.roadieId = str(uuid.uuid4())
            col.collectionReleases.append(colRelease)
            self.logger.info("Added Position [" + str(csvPosition) + "] Release [" + str(release) + "] To Collection")
        col.lastUpdated = arrow.utcnow().datetime
        self.dbSession.commit()
        return True
