# Scanner that looks at a folder and manages MP3 files found
# -- Adds new MP3 files not in database to database
# -- Updates MP3 files found in database but different tag data
# -- Deletes MP3 files found in database but no longer found in folder
import io
import os
import json
import hashlib
import random
import argparse
from datetime import  date, time, datetime
from mongoengine import connect
from resources.models import Artist, ArtistType, Label, Release, ReleaseLabel, Track, TrackRelease
from resources.musicBrainz import MusicBrainz
from resources.id3 import ID3
from resources.logger import Logger


class Scanner(object):

    def __init__(self,readOnly):
        d = os.path.dirname(os.path.realpath(__file__)).split(os.sep)
        path = os.path.join(os.sep.join(d[:-1]), "settings.json")
        with open(path, "r") as rf:
            config = json.load(rf)
        self.dbName = config['MONGODB_SETTINGS']['DB']
        self.host = config['MONGODB_SETTINGS']['host']
        self.thumbnailSize =  config['ROADIE_THUMBNAILS']['Height'], config['ROADIE_THUMBNAILS']['Width']
        self.readOnly = readOnly or False
        self.logger = Logger()

    def inboundMp3Files(self, folder):
        for root, dirs, files in os.walk(folder):
            for filename in files:
                if os.path.splitext(filename)[1] == ".mp3":
                    yield os.path.join(root, filename)


    def scan(self, folder, artist, release):
        if self.readOnly:
            self.logger.debug("[Read Only] Would Process Folder [" + folder + "] With Artist [" + str(artist) + "]")
            return None
        if not artist:
            raise RuntimeError("Invalid Artist")
        if not release:
            raise RuntimeError("Invalid Release")
        if not folder:
            raise RuntimeError("Invalid Folder")
        foundGoodMp3s = False
        foundReleaseTracks = 0
        createdReleaseTracks = 0
        connect(self.dbName, host=self.host)
        mb = MusicBrainz()
        startTime = datetime.now()
        self.logger.info("Scanning Folder [" + folder + "]")
        # Get any existing tracks for folder and verify; update if ID3 tags are different or delete if not found
        if not self.readOnly:
            for track in Track.objects(FilePath=folder):
                filename = os.path.join(track.FilePath, track.FileName)
                # File no longer exists for track
                if not os.path.isfile(filename):
                    if not self.readOnly:
                        Release.objects(Artist = track.Artist).update_one(pull__Tracks__Track = track)
                        track.delete()
                    self.logger.warn("x Deleting Track [" + track.Title + "]: File [" + filename + "] Not Found.")
                else:
                    id3 = ID3(filename)
                    # File has invalid ID3 tags now
                    if not id3.isValid():
                        self.logger.warn("Track Has Invalid or Missing ID3 Tags [" + filename + "]")
                        if not self.readOnly:
                            try:
                                os.remove(filename)
                            except OSError:
                                pass
                            track.delete()
                    else:
                        #See if tags match track details if not matching delete and let scan process find and add it proper
                        id3Hash = hashlib.md5((str(track.Artist.id) + str(id3)).encode('utf-8')).hexdigest()
                        if id3Hash != track.Hash:
                            if not self.readOnly:
                                track.delete()
                            self.logger.warn("x Deleting Track [" + track.Title + "]: Hash Mismatch")
        # For each file found in folder get ID3 info and insert record into Track DB
        scannedMp3Files = 0
        for mp3 in self.inboundMp3Files(folder):
            id3 = ID3(mp3)
            if id3 != None:
                if not id3.isValid():
                    self.logger.warn("Track Has Invalid or Missing ID3 Tags [" + mp3 + "]")
                else:
                    foundGoodMp3s = True
                    track = Track.objects(Title=id3.title, Artist=artist).first()
                    if not track:
                        track = Track(Title=id3.title, Artist=artist)
                        head, tail = os.path.split(mp3)
                        track.FileName = tail
                        track.FilePath = head
                        track.Hash = hashlib.md5((str(artist.id) + str(id3)).encode('utf-8')).hexdigest()
                        mbTracks = mb.tracksForRelease(release.MusicBrainzId)
                        if mbTracks:
                            try:
                                for mbTrackPosition in mbTracks:
                                    for mbt in mbTrackPosition['track-list']:
                                        mbtPosition = int(mbt['position'])
                                        if mbtPosition == id3.track:
                                            track.MusicBrainzId = mbt['recording']['id']
                                            break
                            except:
                                pass
                        track.Length = id3.length
                        if not self.readOnly:
                            Track.save(track)
                        self.logger.info("+ Added Track: Title [" + track.Title + "]")
                    releaseTrack = None
                    for rt in release.Tracks:
                        try:
                            if rt.Track.Hash == track.Hash and \
                               rt.TrackNumber == id3.track and \
                               rt.ReleaseMediaNumber == id3.disc:
                                releaseTrack = rt
                                break;
                        except:
                            pass
                    if not releaseTrack:
                        releaseTrack = TrackRelease(Track=track, TrackNumber=id3.track, ReleaseMediaNumber=id3.disc)
                        releaseTrack.Random = random.randint(1, 1000000)
                        release.Tracks.append(releaseTrack)
                        self.logger.info("+ Added Release Track: Track [" + releaseTrack.Track.Title + "]")
                        if not self.readOnly:
                            Release.save(release)                        
                        createdReleaseTracks += 1
                    else:
                        foundReleaseTracks += 1
                    scannedMp3Files += 1

        elapsedTime = datetime.now() - startTime
        matches = scannedMp3Files == (createdReleaseTracks + foundReleaseTracks)
        self.logger.info(("Scanning Folder [" + folder + "] Complete, Scanned [" +
               ('%02d' % scannedMp3Files) + "] Mp3 Files: Created [" + str(createdReleaseTracks) +
               "] Release Tracks, Found [" + str(foundReleaseTracks) +
               "] Release Tracks. Sane Counts [" + str(matches) + "] Elapsed Time [" + str(elapsedTime) +
               "]").encode('utf-8'))
        return foundGoodMp3s
