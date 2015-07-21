# Process that looks at and processes files/directories in inbound folder
# --- Find or Make Artist For File
# --- Find or Make Release For File
# --- Determine if File Should Be Moved if so move
# --- Each folder call scanner
# --- If folder is empty delete
import linecache
import io
import os
import sys
import shutil
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
from utility import Utility
from scanner import Scanner

class Processor(object):

    def __init__(self,debug,showTagsOnly,dontDeleteInboundFolders):
        with open("../settings.json", "r") as rf:
            config = json.load(rf)
        self.InboundFolder = config['ROADIE_INBOUND_FOLDER']
        self.LibraryFolder = config['ROADIE_LIBRARY_FOLDER']
        self.IsProcessingLibrary = self.InboundFolder == self.LibraryFolder
        # TODO if set then process music files; like clear comments
        self.processingOptions = config['ROADIE_PROCESSING']
        self.isProcessingLibrary = self.LibraryFolder.startswith(self.InboundFolder)
        self.dbName = config['MONGODB_SETTINGS']['DB']
        self.host = config['MONGODB_SETTINGS']['host']
        self.thumbnailSize =  config['ROADIE_THUMBNAILS']['Height'], config['ROADIE_THUMBNAILS']['Width']
        self.debug = debug or False
        self.showTagsOnly = showTagsOnly or False
        self.dontDeleteInboundFolders = dontDeleteInboundFolders or False

    def splitext(path):
        for ext in ['.tar.gz', '.tar.bz2']:
            if path.endswith(ext):
                return path[:-len(ext)], path[-len(ext):]
        return os.path.splitext(path)

    def releaseCoverImages(self, folder):
        try:
            image_filter = ['.jpg', '.jpeg', '.bmp','.png','.gif']
            cover_filter = ['cover', 'front']
            for r,d,f in os.walk(folder):
                for file in f:
                    root, file = os.path.split(file)
                    root, ext = os.path.splitext(file)
                    if ext.lower() in image_filter and root.lower() in cover_filter:
                        yield os.path.join(r, file)
        except:
            Utility.PrintException()
            pass

    def inboundFolders(self):
        for root, dirs, files in os.walk(self.InboundFolder):
            for dir in dirs:
                yield os.path.join(root, dir)

    def folderMp3Files(self, folder):
        for root, dirs, files in os.walk(folder):
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
        return os.path.join(self.artistFolder(artist), "[" + id3.year.zfill(4)[:4] + "] " + self.makeFileFriendly(id3.album))

    def trackName(self, id3):
        return str(id3.track).zfill(2) + " " + self.makeFileFriendly(id3.title) + ".mp3"

    # Determine if the found file should be moved into the library; check for existing and see if better
    def shouldMoveToLibrary(self, artist, artistId, id3, mp3):
        try:
            fileFolderLibPath = os.path.join(self.artistFolder(artist), self.albumFolder(artist, id3))
            head, tail = os.path.split(fileFolderLibPath)
            # File is already in library likely just rescanning for updates
            if self.LibraryFolder.startswith(head):
                return False
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
                existingId3Hash = hashlib.md5((str(artistId) + str(existingId3)).encode('utf-8')).hexdigest()
                id3Hash = hashlib.md5(str(id3).encode('utf-8')).hexdigest()
                if existingId3Hash == id3Hash:
                    # If the hashes are equal its Likely the same file
                    return False
                # If The existing is longer or has a high bitrate then use existing
                if existingId3.length > id3.length and existingId3.bitrate > id3.bitrate:
                    return False
            return True
        except:
            Utility.PrintException()
            return False

    def readImageThumbnailBytesFromFile(self, path):
        try:
            img = Image.open(path).convert('RGB')
            img.thumbnail(self.thumbnailSize)
            b = io.BytesIO()
            img.save(b, "JPEG")
            return b.getvalue()
        except:
            return None

    # If should be moved then move over and return new filename
    def moveToLibrary(self, artist, id3, mp3):
        try:
            newFilename = os.path.join(self.artistFolder(artist), self.albumFolder(artist, id3), self.trackName(id3))
            self.printDebug("Moving [" + mp3 + "] => [" + newFilename + "]")
            move(mp3, newFilename)
            return newFilename
        except:
            Utility.PrintException()
            return None

    def process(self):
        print(("Processing Inbound Folder [" + self.InboundFolder + "]").encode('utf-8'))
        connect(self.dbName, host=self.host)
        mb = MusicBrainz()
        startTime = datetime.now()
        mp3Folder = None
        newMp3Folder = None
        lastID3Artist = None
        lastID3Album = None
        artist = None
        release = None

        # Get all the folder in the InboundFolder
        for mp3Folder in self.inboundFolders():
            foundMp3Files = 0

            # Delete any empty folder if enabled
            if not os.listdir(mp3Folder) and not self.dontDeleteInboundFolders:
                self.printDebug("X Deleted Empty Folder [" + mp3Folder + "]")
                os.rmdir(mp3Folder)
                continue

            # Get all the MP3 files in the Folder and process
            for mp3 in self.folderMp3Files(mp3Folder):
                id3 = ID3(mp3)
                if id3 != None:
                    if not id3.isValid():
                        print("! Track Has Invalid or Missing ID3 Tags [" + mp3 + "]")
                    else:
                        foundMp3Files += 1
                        if self.showTagsOnly:
                            continue
                        # Get Artist
                        if lastID3Artist != id3.artist:
                            artist = None
                        if not artist:
                            lastID3Artist = id3.artist
                            artist = Artist.objects(Name=id3.artist).first()
                        if not artist:
                            # Artist not found create
                            artist = Artist(Name=id3.artist)
                            mbArtist = mb.lookupArtist(id3.artist)
                            if mbArtist:
                                # Populate with some MusicBrainz details
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
                            # See if a file exists to use for the Artist thumbnail
                            artistFile = os.path.join(mp3Folder, "artist.jpg")
                            if os.path.isfile(artistFile):
                                ba = self.readImageThumbnailBytesFromFile(artistFile)
                            if ba:
                                artist.Thumbnail.new_file()
                                artist.Thumbnail.write(ba)
                                artist.Thumbnail.close()
                            # Save The Artist
                            Artist.save(artist)
                            self.printDebug("+ Added Artist Name [" + artist.Name + "]")
                        # Get the Release
                        if lastID3Album != id3.album:
                            release = None
                        if not release:
                            lastID3Album = id3.album
                            release = Release.objects(Title=id3.album, Artist=artist).first()
                        if not release:
                            # Release not found create
                            release = Release(Title=id3.album, Artist=artist, ReleaseDate = "---")
                            mbRelease = mb.searchForRelease(artist.MusicBrainzId, id3.album)
                            if mbRelease:
                                # Populate with some MusicBrainz details
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
                            # Get Release Thumbnail bytes
                            ba = None
                            # See if the tag cover art exists
                            if id3.imageBytes:
                                img = Image.open(io.BytesIO(id3.imageBytes)).convert('RGB')
                                img.thumbnail(self.thumbnailSize)
                                b = io.BytesIO()
                                img.save(b, "JPEG")
                                ba = b.getvalue()
                            else:
                                # See if cover file found in Release Folder
                                coverFile = os.path.join(mp3Folder, "cover.jpg")
                                if os.path.isfile(coverFile):
                                    ba = self.readImageThumbnailBytesFromFile(coverFile)
                                else:
                                    coverFile = os.path.join(mp3Folder, "front.jpg")
                                    if os.path.isfile(coverFile):
                                        ba = self.readImageThumbnailBytesFromFile(coverFile)
                                # if no bytes found see if MusicBrainz has cover art
                                if not ba:
                                    coverArtBytes = mb.lookupCoverArt(release.MusicBrainzId)
                                    if coverArtBytes:
                                        img = Image.open(io.BytesIO(coverArtBytes))
                                        img.thumbnail(self.thumbnailSize)
                                        b = io.BytesIO()
                                        img.save(b, "JPEG")
                                        ba = b.getvalue()
                            # If Cover Art Thumbnail bytes found then set to Release Thumbnail
                            if ba:
                                release.Thumbnail.new_file()
                                release.Thumbnail.write(ba)
                                release.Thumbnail.close()
                            Release.save(release)
                            self.printDebug("+ Added Release: Title [" + release.Title + "]")
                        if self.shouldMoveToLibrary(artist, artist.id, id3, mp3):
                            newMp3 = self.moveToLibrary(artist, id3, mp3)
                            head, tail = os.path.split(newMp3)
                            newMp3Folder = head

            if newMp3Folder:
                for coverImage in self.releaseCoverImages(mp3Folder):
                    im = Image.open(coverImage).convert('RGB')
                    newPath = os.path.join(newMp3Folder, "cover.jpg")
                    self.printDebug("+ Copied Cover File [" + coverImage + "] => [" + newPath + "]")
                    if not self.showTagsOnly:
                        im.save(newPath)

            if not self.showTagsOnly and artist and release and id3:
                scanner = Scanner(self.debug, self.showTagsOnly)
                f = newMp3Folder
                if not f:
                    f = mp3Folder
                scannedSuccesfully = scanner.scan(f, artist, release)
                if not self.isProcessingLibrary and mp3Folder and scannedSuccesfully and not self.dontDeleteInboundFolders:
                    shutil.rmtree(mp3Folder)

            self.printDebug("Processed Folder [" + mp3Folder + "] Found [" + str(foundMp3Files) + "] MP3 Files")

        elapsedTime = datetime.now() - startTime
        print("Processing Complete. Elapsed Time [" + str(elapsedTime) + "]")


p = argparse.ArgumentParser(description='Process Inbound and Library Folders For Updates.')
p.add_argument('--verbose', '-v', action='store_true', help='Enable Verbose Print Statements')
p.add_argument('--dontDeleteInboundFolders', '-d', action='store_true', help='Dont Delete Any Processed Inbound Folders')
p.add_argument('--showTagsOnly', '-st', action='store_true', help='Only Show Tags for Found Files')
args = p.parse_args()

pp = Processor(args.verbose, args.showTagsOnly, args.dontDeleteInboundFolders)
pp.process()