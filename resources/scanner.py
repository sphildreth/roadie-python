# Scanner that looks at a folder and manages MP3 files found
# -- Adds new MP3 files not in database to database
# -- Updates MP3 files found in database but different tag data
# -- Deletes MP3 files found in database but no longer found in folder
import io
import os
import json
import hashlib
import argparse
from datetime import time
from mongoengine import connect
from models import Artist, ArtistType, Label, Release, ReleaseLabel, ThumbnailImage, Track, TrackRelease
from musicBrainz import MusicBrainz
from id3 import ID3


class Scanner:

    def __init__(self,folder,debug,showTagsOnly):
        with open("../settings.json", "r") as rf:
            config = json.load(rf)
        self.folder = folder
        self.dbName = config['MONGODB_SETTINGS']['DB']
        self.host = config['MONGODB_SETTINGS']['host']
        self.thumbnailSize =  config['ROADIE_THUMBNAILS']['Height'], config['ROADIE_THUMBNAILS']['Width']
        self.debug = debug or False
        self.showTagsOnly = showTagsOnly or False


    def inboundMp3Files(self):
        for root, dirs, files in os.walk(self.folder):
            for filename in files:
                if os.path.splitext(filename)[1] == ".mp3":
                    yield os.path.join(root, filename)


    def printDebug(self, message):
        if self.debug:
            print(message)

    def scan(self):
        print("Scanning Folder [" + self.folder + "]")
        connect(self.dbName, host=self.host)
        mb = MusicBrainz()
        startTime = time()
        for mp3 in self.inboundMp3Files():
            try:
                id3 = ID3(mp3)
            except:
                print("Unexpected error:", sys.exc_info())
                id3 = None
            if id3 != None:
                self.printDebug("--- IsValid: [" + str(id3.isValid()) + "] " +  id3.artist + " : (" + str(id3.year) + ") "\
                          + id3.album + " : " + str(id3.disc) + "::" + str(id3.track).zfill(2) + " " + id3.title + " ("\
                          + str(id3.bitrate) + "bps::" + str(id3.length) + ")" )
                if not id3.isValid():
                    print("Track Has Invalid or Missing ID3 Tags [" + mp3 + "]")
                else:
                    if self.showTagsOnly:
                        continue
                    artist = Artist.objects(Name=id3.artist).first()
                    if not artist:
                        raise RuntimeError("Artist [" + id3.artist + "] Not found")
                    release = Release.objects(Title=id3.album, Artist=artist).first()
                    if not release:
                        raise RuntimeError("Release [" + id3.album + "] Not found")
                    track = Track.objects(Title=id3.title, Artist=artist).first()
                    if not track:
                        track = Track(Title=id3.title, Artist=artist)
                        head, tail = os.path.split(mp3)
                        track.FileName = tail
                        track.FilePath = head
                        track.Hash = hashlib.md5(str(id3).encode('utf-8')).hexdigest()
                        mbTracks = mb.tracksForRelease(release.MusicBrainzId)
                        if mbTracks:
                            for mbTrackPosition in mbTracks:
                                for mbt in mbTrackPosition['track-list']:
                                    if mbt['position'] == id3.track:
                                        track.MusicBrainzId = mbt['recording']['id']
                                        break
                        track.Length = id3.length
                        object_id = Track.save(track)
                        self.printDebug("Added Track: Title [" + release.Title + "], Id [" + str(object_id) + "]")
                    releaseTrack = None
                    for rt in release.Tracks:
                        if rt.Track.Hash == track.Hash and rt.TrackNumber == id3.track and rt.ReleaseMediaNumber == id3.disc:
                            releaseTrack = rt
                            break;
                    if not releaseTrack:
                        releaseTrack = TrackRelease(Track=track, TrackNumber=id3.track, ReleaseMediaNumber=id3.disc)
                        release.Tracks.append(releaseTrack)
                        object_id = Release.save(release)
                        self.printDebug("Added Release Track: Track [" + releaseTrack.Track.Title + "], Id [" + str(object_id) + "]")
        # TODO Get any tracks for folder and verify they exist
        elapsedTime = time() - startTime
        print("Scanning Complete. Elapsed Time [" + str(elapsedTime))

parser = argparse.ArgumentParser(description='Scan given Folder for DB Updates.')
parser.add_argument('--folder', '-f', required=True, help='Folder To Scan')
parser.add_argument('--verbose', '-v', action='store_true', help='Enable Verbose Print Statements')
parser.add_argument('--showTagsOnly', '-st', action='store_true', help='Only Show Tags for Found Files')
args = parser.parse_args()

scanner = Scanner(args.folder, args.verbose, args.showTagsOnly)
scanner.scan()