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
        super().__init__(config)

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
                        release.genres = []
                        self.session.delete(release)
                    self.logger.warn(
                        "X Deleting Release [" + str(release) + "] Folder [" + releaseFolder + "] Not Found")
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
                                    pass
                            if not isTrackFilePresent:
                                if not self.readOnly:
                                    track.filePath = None
                                    track.fileName = None
                                    track.fileSize = 0
                                    track.hash = None
                                self.logger.warn(
                                    "X Missing Track [" + str(track.info(includePathInfo=True)) + "] File [" + str(
                                        trackFilename) + "]")
                                issuesFound = True
                                release.libraryStatus = 'Incomplete'
                            else:
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
                    if releaseTrackCount > 1:
                        release.trackCount = releaseTrackCount
                    release.lastUpdated = arrow.utcnow().datetime
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
