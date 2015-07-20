# Process that looks at and processes files/directories in inbound folder
# --- Each folder call scanner
# --- If folder is empty delete
import io
import os
import sys
import json
import hashlib
import argparse
from PIL import Image
from datetime import  date, time, datetime
from dateutil.parser import *
from goldfinch import validFileName as vfn
from shutil import move
from mongoengine import connect
from models import Artist, ArtistType, Label, Release, ReleaseLabel, ThumbnailImage, Track, TrackRelease
from musicBrainz import MusicBrainz
from id3 import ID3


class Processor:

    def __init__(self,debug,showTagsOnly):
        with open("../settings.json", "r") as rf:
            config = json.load(rf)
        self.InboundFolder = config['ROADIE_INBOUND_FOLDER']
        self.LibraryFolder = config['ROADIE_LIBRARY_FOLDER']
        self.dbName = config['MONGODB_SETTINGS']['DB']
        self.host = config['MONGODB_SETTINGS']['host']
        self.thumbnailSize =  config['ROADIE_THUMBNAILS']['Height'], config['ROADIE_THUMBNAILS']['Width']
        self.debug = debug or False
        self.showTagsOnly = showTagsOnly or False

    def inboundCoverImages(self):
        try:
            image_filter = ['jpg','bmp','png','gif']
            cover_filter = ['cover', 'front']
            for r,d,f in os.walk(self.InboundFolder):
                for file in f:
                    head, tail = file.split('.')
                    if file[-3:] in image_filter and head in cover_filter:
                        yield os.path.join(r, file)
        except:
            print("Unexpected error:", sys.exc_info())
            pass

    def inboundMp3Files(self):
        for root, dirs, files in os.walk(self.InboundFolder):
            for filename in files:
                if os.path.splitext(filename)[1] == ".mp3":
                    yield os.path.join(root, filename)


    def makeFileFriendly(self,string):
        return vfn(string, space="keep").decode('utf-8')

    def printDebug(self, message):
        if self.debug:
            print(message.encode('utf-8'))

    def artistFolder(self, artist):
        artistFolder = artist.SortName or artist.Name
        return os.path.join(self.LibraryFolder, self.makeFileFriendly(artistFolder))

    def albumFolder(self, artist, id3):
        return os.path.join(self.artistFolder(artist), "[" + id3.year.zfill(4) + "] " + self.makeFileFriendly(id3.album))

    def trackName(self, id3):
        return str(id3.track).zfill(2) + " " + self.makeFileFriendly(id3.title) + ".mp3"

    # Determine if the found file should be moved into the library; check for existing and see if better
    def shouldMoveToLibrary(self, artist, id3, mp3):
        try:
            fileFolderLibPath = os.path.join(self.artistFolder(artist), self.albumFolder(artist, id3))
            os.makedirs(fileFolderLibPath, exist_ok=True)
            fullFileLibPath = os.path.join(fileFolderLibPath, self.makeFileFriendly(self.trackName(id3)))
            if not os.path.isfile(fullFileLibPath):
                # Does not exist copy it over
                return True
            else:
                # Does exist see if the one being copied is 'better' then the existing
                existingId3 = ID3(fullFileLibPath)
                if not existingId3.isValid():
                    return True
                existingId3Hash = hashlib.md5(str(existingId3).encode('utf-8')).hexdigest()
                id3Hash = hashlib.md5(str(id3).encode('utf-8')).hexdigest()
                if existingId3Hash == id3Hash:
                    # If the hashes are equal its Likely the same file
                    return False
                # If The existing is longer or has a high bitrate then use existing
                if existingId3.length > id3.length and existingId3.bitrate > id3.bitrate:
                    return False
            return True
        except:
            print("Unexpected error:", sys.exc_info())
            return False

    def readImageThumbnailBytesFromFile(self, path):
        img = Image.open(path)
        img.thumbnail(self.thumbnailSize)
        b = io.BytesIO()
        img.save(b, "JPEG")
        return b.getvalue()

    # If should be moved then move over and return new filename
    def moveToLibrary(self, artist, id3, mp3):
        try:
            newFilename = os.path.join(self.artistFolder(artist), self.albumFolder(artist, id3), self.trackName(id3))
            self.printDebug("Moving [" + mp3 + "] => [" + newFilename + "]")
            move(mp3, newFilename)
            return newFilename
        except:
            print("Unexpected error:", sys.exc_info())
            return None

    def process(self):
        print("Scanning Folder [" + self.InboundFolder + "]")
        connect(self.dbName, host=self.host)
        mb = MusicBrainz()
        startTime = datetime.now()
        mp3Folder = None
        lastMp3Folder = None
        for mp3 in self.inboundMp3Files():
            mp3Folder = os.path.split(mp3)[0]
            if mp3Folder == lastMp3Folder:
                continue
            try:
                id3 = ID3(mp3)
            except:
                print("Unexpected error:", sys.exc_info())
                id3 = None
            if id3 != None:
                if not id3.isValid():
                    print("*! Track Has Invalid or Missing ID3 Tags [" + mp3 + "]")
                else:
                    if self.showTagsOnly:
                        continue
                    artist = Artist.objects(Name=id3.artist).first()
                    if artist:
                        self.printDebug("\ Found Artist Name [" + str(artist) + "]")
                    else:
                        artist = Artist(Name=id3.artist)
                        mbArtist = mb.lookupArtist(id3.artist)
                        if mbArtist:
                            artist.MusicBrainzId = mbArtist['id']
                            begin = None
                            if 'life-span' in mbArtist:
                                if 'begin' in mbArtist['life-span']:
                                    begin = parse(mbArtist['life-span']['begin'])
                            artist.BeginDate = begin
                            ended =mbArtist['life-span']['ended']
                            if ended != "false":
                                ended = None
                                if 'life-span' in mbArtist:
                                    if 'end' in mbArtist['life-span']:
                                        ended = parse(mbArtist['life-span']['end'])
                                artist.EndDate = ended
                            artistType = None
                            if 'type' in mbArtist:
                                artistType = ArtistType.objects(Name=mbArtist['type']).first()
                            if artistType:
                                artist.ArtistType = artistType
                            artist.SortName = mbArtist['sort-name']
                            tags = []
                            if 'tag-list' in mbArtist:
                                for tag in mbArtist['tag-list']:
                                    if tag:
                                        tags.append(tag['name'].strip().title())
                            artist.Tags = tags
                            alias = []
                            if 'alias-list' in mbArtist:
                                for a in mbArtist['alias-list']:
                                    if a and 'alias' in a:
                                        alias.append(a['alias'].strip().title())
                            artist.AlternateNames = alias
                        ba = None
                        artistFile = os.path.join(mp3Folder, "artist.jpg")
                        if os.path.isfile(artistFile):
                            ba = self.readImageThumbnailBytesFromFile(artistFile)
                        if ba:
                            artist.Thumbnail.new_file()
                            artist.Thumbnail.write(ba)
                            artist.Thumbnail.close()
                        object_id = Artist.save(artist)
                        self.printDebug("+ Added Artist Name [" + artist.Name + "], Id [" + str(object_id) + "]")
                    release = Release.objects(Title=id3.album, Artist=artist).first()
                    if release:
                        self.printDebug("| Found Release [" + str(release) + "]")
                    else:
                        release = Release(Title=id3.album, Artist=artist, ReleaseDate = "---")
                        mbRelease = mb.searchForRelease(artist.MusicBrainzId, id3.album)
                        if mbRelease:
                            release.Artist = artist
                            date = None;
                            if id3.year:
                                date = id3.year
                            if 'date' in mbRelease and not date:
                                date = parse(mbRelease['date'])
                            release.ReleaseDate = date or '---'
                            release.MusicBrainzId = mbRelease['id']
                            mbMedium = mbRelease['medium-list'][0]
                            if not 'track-count' in mbMedium:
                                mbMedium = mbRelease['medium-list'][1]
                            release.TrackCount = mbMedium['track-count']
                            release.DiscCount = mbMedium['disc-count'] or 1
                            if 'label-info-list' in mbRelease:
                                for mbLabel in mbRelease['label-info-list']:
                                    label = None
                                    if 'name' in mbLabel['label']:
                                        mbLabelName = mbLabel['label']['name']
                                        if mbLabelName:
                                            mbLabelName = mbLabelName.strip().title()
                                            label = Label.objects(Name=mbLabelName).first()
                                            if not label:
                                                label = Label(Name=mbLabelName)
                                                label.MusicBrainzId = mbLabel['label']['id']
                                                object_id = Label.save(label)
                                                self.printDebug("+ Added Label Name [" + label.Name + "], Id [" + str(object_id) + "]")
                                    if label:
                                        catalogNumber = None
                                        if 'catalog-number' in mbLabel:
                                            catalogNumber = mbLabel['catalog-number'].strip().title()
                                        releaseLabel = ReleaseLabel(Label=label, CatalogNumber=catalogNumber)
                                        release.Labels.append(releaseLabel)
                            tags = []
                            if 'release-group' in mbRelease:
                                if 'type' in mbRelease['release-group']:
                                    tags.append(mbRelease['release-group']['type'].strip().title())
                            format = None
                            if 'format' in mbMedium:
                                format = mbMedium['format']
                            if format:
                                tags.append(format)
                            release.Tags = tags
                            if id3.imageBytes:
                                try:
                                    img = Image.open(io.BytesIO(id3.imageBytes))
                                    img.thumbnail(self.thumbnailSize)
                                    b = io.BytesIO()
                                    img.save(b, "JPEG")
                                except:
                                    img = Image.open(io.BytesIO(id3.imageBytes)).convert('RGB')
                                    img.thumbnail(self.thumbnailSize)
                                    b = io.BytesIO()
                                    img.save(b, "JPEG")
                                ba = b.getvalue()
                                release.Thumbnail.new_file()
                                release.Thumbnail.write(ba)
                                release.Thumbnail.close()
                            else:
                                ba = None
                                coverFile = os.path.join(mp3Folder, "cover.jpg")
                                if os.path.isfile(coverFile):
                                    ba = self.readImageThumbnailBytesFromFile(coverFile)
                                else:
                                    coverFile = os.path.join(mp3Folder, "front.jpg")
                                    if os.path.isfile(coverFile):
                                        ba = self.readImageThumbnailBytesFromFile(coverFile)

                                if not ba:
                                    coverArtBytes = mb.lookupCoverArt(release.MusicBrainzId)
                                    if coverArtBytes:
                                        self.printDebug("Using MusicBrainz Cover Art")
                                        img = Image.open(io.BytesIO(coverArtBytes))
                                        img.thumbnail(self.thumbnailSize)
                                        b = io.BytesIO()
                                        img.save(b, "JPEG")
                                        ba = b.getvalue()

                                if ba:
                                    release.Thumbnail.new_file()
                                    release.Thumbnail.write(ba)
                                    release.Thumbnail.close()
                        object_id = Release.save(release)
                        self.printDebug("+ Added Release: Title [" + release.Title + "], Id [" + str(object_id) + "]")
            lastMp3Folder = mp3Folder

        if mp3Folder:
            for coverImage in self.inboundCoverImages():
                im = Image.open(coverImage)
                newPath = os.path.join(mp3Folder, "cover.jpg")
                self.printDebug("Copied Cover File [" + newPath + "]")
                if not self.showTagsOnly:
                    im.save(newPath)

        elapsedTime = datetime.now() - startTime
        print("Scanning Complete. Elapsed Time [" + str(elapsedTime) + "]")


p = argparse.ArgumentParser(description='Scan Inbound and Library Folders For Updates.')
p.add_argument('--verbose', '-v', action='store_true', help='Enable Verbose Print Statements')
p.add_argument('--showTagsOnly', '-st', action='store_true', help='Only Show Tags for Found Files')
args = p.parse_args()

pp = Processor(args.verbose, args.showTagsOnly)
pp.process()