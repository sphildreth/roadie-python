# Scanner that looks at a folder and manages MP3 files found
# -- Adds new MP3 files not in database to database
# -- Updates MP3 files found in database but different tag data
# -- Deletes MP3 files found in database but no longer found in folder
import io
import os
import json
import hashlib
import argparse
from datetime import  date, time, datetime
from mongoengine import connect
from models import Artist, ArtistType, Label, Release, ReleaseLabel, ThumbnailImage, Track, TrackRelease
from musicBrainz import MusicBrainz
from id3 import ID3


class Scanner(object):

    def __init__(self,debug,showTagsOnly):
        with open("../settings.json", "r") as rf:
            config = json.load(rf)
        self.dbName = config['MONGODB_SETTINGS']['DB']
        self.host = config['MONGODB_SETTINGS']['host']
        self.thumbnailSize =  config['ROADIE_THUMBNAILS']['Height'], config['ROADIE_THUMBNAILS']['Width']
        self.debug = debug or False
        self.showTagsOnly = showTagsOnly or False


    def inboundMp3Files(self, folder):
        for root, dirs, files in os.walk(folder):
            for filename in files:
                if os.path.splitext(filename)[1] == ".mp3":
                    yield os.path.join(root, filename)


    def printDebug(self, message):
        if self.debug:
            print(message.encode('utf-8'))

    def scan(self, folder, artist, release):
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
        self.printDebug("Scanning Folder [" + folder + "]")
        # Get any existing tracks for folder and verify; update if ID3 tags are different or delete if not found
        if not self.showTagsOnly:
            for track in Track.objects(FilePath=folder):
                filename = os.path.join(track.FilePath, track.FileName)
                # File no longer exists for track
                if not os.path.isfile(filename):
                    self.printDebug("x Deleting Track [" + track.Title + "]: File [" + filename + "] Not Found.")
                    Release.objects(Artist = track.Artist).update_one(pull__Tracks__Track = track)
                    track.delete()
                else:
                    id3 = ID3(filename)
                    # File has invalid ID3 tags now
                    if not id3.isValid():
                        print("Track Has Invalid or Missing ID3 Tags [" + filename + "]")
                        try:
                            os.remove(filename)
                        except OSError:
                            pass
                        track.delete()
                    else:
                        #See if tags match track details if not matching delete and let scan process find and add it proper
                        id3Hash = hashlib.md5((str(track.Artist.id) + str(id3)).encode('utf-8')).hexdigest()
                        if id3Hash != track.Hash:
                            self.printDebug("x Deleting Track [" + track.Title + "]: Hash Mismatch")
                            track.delete()

        # For each file found in folder get ID3 info and insert record into Track DB
        scannedMp3Files = 0
        for mp3 in self.inboundMp3Files(folder):
            id3 = ID3(mp3)
            if id3 != None:
                if not id3.isValid():
                    print("Track Has Invalid or Missing ID3 Tags [" + mp3 + "]")
                else:
                    foundGoodMp3s = True
                    if self.showTagsOnly:
                        continue
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
                        object_id = Track.save(track)
                        self.printDebug("+ Added Track: Title [" + release.Title + "], Id [" + str(object_id) + "]")
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
                        release.Tracks.append(releaseTrack)
                        object_id = Release.save(release)
                        self.printDebug("+ Added Release Track: Track [" + releaseTrack.Track.Title + "], Id [" + str(object_id) + "]")
                        createdReleaseTracks += 1
                    else:
                        foundReleaseTracks += 1
                    scannedMp3Files += 1

        elapsedTime = datetime.now() - startTime
        matches = scannedMp3Files == (createdReleaseTracks + foundReleaseTracks)
        print(("Scanning Folder [" + folder + "] Complete, Scanned [" +
               ('%02d' % scannedMp3Files) + "] Mp3 Files: Created [" + str(createdReleaseTracks) +
               "] Release Tracks, Found [" + str(foundReleaseTracks) +
               "] Release Tracks. Sane Counts [" + str(matches) + "] Elapsed Time [" + str(elapsedTime) +
               "]").encode('utf-8'))
        return foundGoodMp3s
