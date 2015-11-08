import os

from resources.common import *
from resources.logger import Logger
from resources.models.Artist import Artist
from resources.processingBase import ProcessorBase


class Validator(ProcessorBase):
    def __init__(self, config, dbConn, dbSession, readOnly):
        self.config = config
        self.libraryFolder = config['ROADIE_LIBRARY_FOLDER']
        if 'ROADIE_TRACK_PATH_REPLACE' in config:
            self.trackPathReplace = config['ROADIE_TRACK_PATH_REPLACE']
        self.readOnly = readOnly or False
        self.logger = Logger()
        self.conn = dbConn
        self.session = dbSession

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
                    #  if not self.readOnly:
                    #       self.session.delete(release)
                    issuesFound = True
                    self.logger.warn(
                        "X Deleting Release [" + str(release) + "] Folder [" + releaseFolder + "] Not Found")
                    continue
                releaseTrackCount = 0
                releaseMediaCount = 0
                # If release is not already complete, set to complete unless its found otherwise
                if release.libraryStatus != 'Complete':
                    release.libraryStatus = 'Complete'
                for releaseMedia in release.media:
                    releaseMediaCount += 1
                    releaseMediaTrackCount = 0
                    for track in sorted(releaseMedia.tracks, key=lambda tt: tt.trackNumber):
                        try:
                            trackFilename = self.pathToTrack(track)
                            if not os.path.isfile(trackFilename):
                                if not self.readOnly:
                                #    self.session.delete(track)
                                self.logger.warn(
                                    "X Deleting Track [" + str(track) + "] File [" + trackFilename + "] not found")
                                issuesFound = True
                            else:
                                releaseMediaTrackCount += 1
                                releaseTrackCount += 1
                                if not isEqual(track.trackNumber, releaseMediaTrackCount):
                                    self.logger.warn("! Track Number Sequence InCorrect Is [" +
                                                     str(releaseMediaTrackCount) + "] Expected [" +
                                                     str(track.trackNumber) + "]")
                                    release.libraryStatus = 'Incomplete'
                                    issuesFound = True
                        except:
                            pass
                    if not self.readOnly:
                        releaseMedia.trackCount = releaseMediaTrackCount
                if not self.readOnly:
                    release.mediaCount = releaseMediaCount
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
