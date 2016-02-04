import os

from resources.common import *
from resources.logger import Logger
from resources.models.Artist import Artist
from resources.processingBase import ProcessorBase


class Validator(ProcessorBase):
    def __init__(self, config, dbConn, dbSession, readOnly):
        self.readOnly = readOnly or False
        self.logger = Logger()
        self.conn = dbConn
        self.session = dbSession
        super().__init__(config, self.logger)

    def validateArtists(self):
        for artist in self.session.query(Artist).all():
            self.validate(artist)

    def validate(self, artist, onlyValidateRelease=None):
        """
        Do sanity checks on given Artist
        :param onlyValidateRelease: Release
        :param artist: Artist
        :return:
        """
        if not artist:
            raise RuntimeError("Invalid Artist")
        if not self.config:
            raise RuntimeError("Invalid Configuration")
        if not self.libraryFolder:
            raise RuntimeError("Invalid Configuration: Library Folder Not Set")
        now = arrow.utcnow().datetime
        try:
            for release in artist.releases:
                issuesFound = False
                if onlyValidateRelease and release.roadieId != onlyValidateRelease.roadieId:
                    continue
                releaseFolder = self.albumFolder(artist, release.releaseDate.strftime('%Y'), release.title)
                try:
                    folderExists = os.path.exists(releaseFolder)
                except:
                    folderExists = False
                if not folderExists:
                    if not self.readOnly:
                        for media in release.media:
                            for track in media.tracks:
                                locatedTrackInfo = self.tryToFindFileForTrack(artist, track)
                                if locatedTrackInfo:
                                    movedFile = self.moveToLibrary(artist, locatedTrackInfo['id3'],
                                                                   locatedTrackInfo['fileName'])
                                    if movedFile:
                                        self.logger.warn(
                                            "! Moved File From [" + locatedTrackInfo[
                                                'fileName'] + "] To [" + movedFile + "]")
                                        folderExists = True
                                else:
                                    track.filePath = None
                                    track.fileName = None
                                    track.fileSize = 0
                                    track.hash = None
                                track.lastUpdated = now
                    if not folderExists:
                        release.libraryStatus = 'Incomplete'
                        self.logger.warn(
                            "X Marking Release Missing [" + str(
                                release) + "] Missing Folder [" + releaseFolder + "] Not Found")
                        continue
                releaseTrackCount = 0
                # If release is not already complete, set to complete unless its found otherwise
                release.libraryStatus = 'Complete'
                releaseMediaWithTracks = []
                for releaseMedia in release.media:
                    releaseMediaTrackCount = 0
                    for track in sorted(releaseMedia.tracks, key=lambda tt: tt.trackNumber):
                        try:
                            trackFilename = self.pathToTrack(track)
                            isTrackFilePresent = False
                            if trackFilename:
                                try:
                                    isTrackFilePresent = os.path.isfile(trackFilename)
                                except:
                                    self.logger.exception()
                                    pass
                            if not isTrackFilePresent:
                                # See if track exists in another folder and title was renamed so folder no longer
                                #   matches what it is expected to be
                                if not self.readOnly:
                                    locatedTrackInfo = self.tryToFindFileForTrack(artist, track)
                                    if locatedTrackInfo and not isEqual(trackFilename, locatedTrackInfo['fileName']):
                                        movedFile = self.moveToLibrary(artist, locatedTrackInfo['id3'],
                                                                       locatedTrackInfo['fileName'])
                                        if movedFile:
                                            head, tail = os.path.split(movedFile)
                                            headNoLibrary = head.replace(self.config['ROADIE_LIBRARY_FOLDER'], "")
                                            trackHash = self.makeTrackHash(artist.roadieId, movedFile)
                                            track.fileName = tail
                                            track.filePath = headNoLibrary
                                            track.hash = trackHash
                                            track.fileSize = os.path.getsize(movedFile)
                                            track.lastUpdated = now
                                            self.logger.warn(
                                                "! Located Track [" + str(track.info(includePathInfo=True)) + "]")
                                            isTrackFilePresent = True
                                    else:
                                        track.filePath = None
                                        track.fileName = None
                                        track.fileSize = 0
                                        track.hash = None
                                        track.lastUpdated = now
                                        self.logger.warn(
                                            "X Missing Track [" + str(
                                                track.info(includePathInfo=True)) + "] File [" + str(
                                                trackFilename) + "]")
                                        issuesFound = True
                                        release.libraryStatus = 'Incomplete'
                            if isTrackFilePresent:
                                releaseMediaTrackCount += 1
                                releaseTrackCount += 1
                                if not isEqual(track.trackNumber, releaseMediaTrackCount):
                                    self.logger.warn("! Track Number Sequence InCorrect Is [" +
                                                     str(track.trackNumber) + "] Expected [" +
                                                     str(releaseMediaTrackCount) + "]")
                                    release.libraryStatus = 'Incomplete'
                                    issuesFound = True
                        except:
                            self.logger.exception()
                            issuesFound = True
                            pass
                    releaseMedia.trackCount = releaseMediaTrackCount
                    if releaseMedia.trackCount > 0:
                        releaseMediaWithTracks.append(releaseMedia)
                if not self.readOnly:
                    release.media = releaseMediaWithTracks
                    release.mediaCount = len(releaseMediaWithTracks)
                    # Seems not likely that a release only has a single track; more likely missing unknown tracks
                    if releaseTrackCount > 1 and release.trackCount < 2:
                        release.trackCount = releaseTrackCount
                    release.lastUpdated = now
                self.logger.info("Validated Artist [" + str(artist) + "], " +
                                 "Release [" + str(release) + "], " +
                                 "IssuesFound [" + str(issuesFound) + "]")
            if not self.readOnly:
                self.session.commit()
            else:
                self.session.rollback()
        except:
            self.logger.exception("Validating Artist, Rolling Back Session Transactions")
            try:
                self.session.rollback()
            except:
                pass
