# Scanner to find and add new music files
import io
import os
import json
import hashlib
import shlex
import argparse
import sys
import musicbrainzngs
import tempfile
import mutagen
from PIL import Image
from dateutil.parser import *
from datetime import *
from goldfinch import validFileName as vfn
from mutagen.mp3 import MP3
from shutil import move
from mongoengine import connect
from models import Artist, ArtistType, Label, Release, ReleaseLabel, ThumbnailImage, Track, TrackRelease


class MusicBrainz:

    def __init__(self):
        musicbrainzngs.set_useragent("Roadie", "0.1", "https://github.com/sphildreth/roadie")
        self.artists = {}
        self.searchReleases = {}
        self.releases = {}

    def lookupArtist(self, name):
        cacheKey = name.replace(" ", "")
        if cacheKey in self.artists:
            return self.artists[cacheKey]

        try:
            print("Getting Artist [" + name + "] From MusicBrainz")
            result = musicbrainzngs.search_artists(artist=name, type="group")
        except:
            result = None

        if result and result['artist-list'][0]:
            self.artists[cacheKey] = result['artist-list'][0]
            return self.artists[cacheKey]


    def searchForRelease(self, artistId, title):
        cacheKey = artistId + "." + title.replace(" ", "")
        if cacheKey in self.searchReleases:
            return self.searchReleases[cacheKey]

        try:
            print("Search For Release [" + title + "] From MusicBrainz")
            result = musicbrainzngs.search_releases(limit=1, arid=artistId, release=title)
        except:
            result = None

        if result and result['release-list'][0]:
            self.searchReleases[cacheKey] = result['release-list'][0]
            return self.searchReleases[cacheKey]


    def lookupRelease(self, releaseId):
        if releaseId in self.releases:
            return self.releases[releaseId]

        try:
            print("Getting Release [" + releaseId + "] From MusicBrainz")
            result = musicbrainzngs.get_release_by_id(releaseId, includes=['recordings'])
        except:
            result = None

        if result:
            self.releases[releaseId] = result['release']
            return self.releases[releaseId]

    def tracksForRelease(self, relasedId):
        release = self.lookupRelease(relasedId)
        if release:
            return release['medium-list']


    def lookupCoverArt(self, releaseId):
        try:
            return musicbrainzngs.get_image_front(releaseId)
        except:
            return None



class ID3:

    def __init__(self,path):
        self._load(path)

    def isValid(self):
        if self.artist and self.year and self.album and self.track and self.title and self.bitrate and self.length:
            return True
        else:
            return False

    def __str__(self):
        return self.artist + "." + str(self.year) + "." + self.album  + "." + str(self.track) + "." + self.title + "." + str(self.bitrate) + "." + str(self.length)

    def _load(self, filename):
        short_tags = full_tags = mutagen.File(filename)
        comments = []
        if isinstance(full_tags, mutagen.mp3.MP3):
            for key in short_tags:
                if key[0:4] == 'COMM':
                    if(short_tags[key].desc == ''):
                        comments.append(short_tags[key].text[0])
            short_tags = mutagen.mp3.MP3(filename, ID3 = mutagen.easyid3.EasyID3)
        comments.append('')
        self.album = short_tags.get('album', [''])[0].strip()
        self.artist = short_tags.get('artist', [''])[0].strip()
        self.duration = "%u:%.2d" % (full_tags.info.length / 60, full_tags.info.length % 60)
        trackNumber = short_tags.get('tracknumber', [''])[0]
        if("/" in trackNumber):
            self.track = int(trackNumber.split("/")[0])
        else:
            self.track = int(trackNumber)
        self.length = full_tags.info.length
        self.bitrate = full_tags.info.bitrate
        discNumber = short_tags.get('discnumber', [''])[0]
        if discNumber:
            self.disc = int(discNumber)
        else:
            self.disc = 1;
        self.year = short_tags.get('date', [''])[0]
        self.title = short_tags.get('title', [''])[0].strip()
        self.comment = comments[0]
        self.genre = ''
        genres = short_tags.get('genre', [''])
        if len(genres) > 0:
            self.genre = genres[0]
        self.size = os.stat(filename).st_size
        self.imageBytes = None
        if 'APIC:' in  full_tags.tags:
            self.imageBytes = full_tags.tags._DictProxy__dict['APIC:'].data



class Scanner:

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
        image_filter = ['jpg','bmp','png','gif']
        cover_filter = ['cover', 'front']
        for r,d,f in os.walk(self.InboundFolder):
            for file in f:
                head, tail = file.split('.')
                if file[-3:] in image_filter and head in cover_filter:
                    yield os.path.join(r, file)

    def inboundMp3Files(self):
        for root, dirs, files in os.walk(self.InboundFolder):
            for filename in files:
                if os.path.splitext(filename)[1] == ".mp3":
                    yield os.path.join(root, filename)


    def makeFileFriendly(self,string):
        return vfn(string, space="keep").decode('utf-8')

    def printDebug(self, message):
        if self.debug:
            print(message)

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

    def scan(self):
        print("Scanning Folder [" + self.InboundFolder + "]")
        print("Destination Folder [" + self.LibraryFolder + "]")
        connect(self.dbName, host=self.host)
        mb = MusicBrainz()

        albumFolder = None
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
                        pass
                    artist = Artist.objects(Name=id3.artist).first()
                    if not artist:
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
                                    tags.append(tag['name'])
                            artist.Tags = tags
                            alias = []
                            if 'alias-list' in mbArtist:
                                for a in mbArtist['alias-list']:
                                    alias.append(a['alias'])
                            artist.AlternateNames = alias
                        object_id = Artist.save(artist)
                        self.printDebug("Added Artist Name [" + artist.Name + "], Id [" + str(object_id) + "]")
                    if not self.shouldMoveToLibrary(artist, id3, mp3):
                        self.printDebug("Skipped Moving To Library [" + mp3 + "]")
                        pass
                    newFilePath = self.moveToLibrary(artist, id3, mp3)
                    if not newFilePath:
                        self.printDebug("Skipped Moving To Library [" + mp3 + "]")
                        pass
                    albumFolder = os.path.split(newFilePath)[0]
                    release = Release.objects(Title=id3.album, Artist=artist).first()
                    if not release:
                        release = Release(Title=id3.album, Artist=artist)
                        mbRelease = mb.searchForRelease(artist.MusicBrainzId, id3.album)
                        if mbRelease:
                            release.Artist = artist
                            date = None;
                            if id3.year:
                                date = parse(id3.year)
                            if 'date' in mbRelease and not date:
                                date = parse(mbRelease['date]'])
                            if date:
                                release.ReleaseDate = date
                            release.MusicBrainzId = mbRelease['id']
                            mbMedium = mbRelease['medium-list'][0]
                            if not 'track-count' in mbMedium:
                                mbMedium = mbRelease['medium-list'][1]
                            release.TrackCount = mbMedium['track-count']
                            release.DiscCount = mbMedium['disc-count'] or 1
                            if 'label-info-list' in mbRelease:
                                for mbLabel in mbRelease['label-info-list']:
                                    label = Label.objects(Name=mbLabel['label']['name']).first()
                                    if not label:
                                        label = Label(Name=mbLabel['label']['name'])
                                        label.MusicBrainzId = mbLabel['label']['id']
                                        object_id = Label.save(label)
                                        self.printDebug("Added Label Name [" + label.Name + "], Id [" + str(object_id) + "]")
                                    # need to see if label is already associated with release
                                    catalogNumber = None
                                    if 'catalog-number' in mbLabel:
                                        catalogNumber = mbLabel['catalog-number']
                                    releaseLabel = ReleaseLabel(Label=label, CatalogNumber=catalogNumber)
                                release.Labels.append(releaseLabel)
                            tags = []
                            tags.append(mbRelease['release-group']['type'])
                            format = None
                            if 'format' in mbMedium:
                                format = mbMedium['format']
                            if format:
                                tags.append(format)
                            release.Tags = tags
                            if id3.imageBytes:
                                img = Image.open(io.BytesIO(id3.imageBytes))
                                img.thumbnail(self.thumbnailSize)
                                b = io.BytesIO()
                                img.save(b, "JPEG")
                                ba = b.getvalue()
                                release.Thumbnail.new_file()
                                release.Thumbnail.write(ba)
                                release.Thumbnail.close()
                            else:
                                # TODO see if 'cover' file exists and load from that else query MusicBrainz
                                coverArtBytes = mb.lookupCoverArt(release.MusicBrainzId)
                                if coverArtBytes:
                                    img = Image.open(io.BytesIO(coverArtBytes))
                                    img.thumbnail(self.thumbnailSize)
                                    b = io.BytesIO()
                                    img.save(b, "JPEG")
                                    ba = b.getvalue()
                                    release.Thumbnail.new_file()
                                    release.Thumbnail.write(ba)
                                    release.Thumbnail.close()
                        object_id = Release.save(release)
                        self.printDebug("Added Release: Title [" + release.Title + "], Id [" + str(object_id) + "]")
                    track = Track.objects(Title=id3.title, Artist=artist).first()
                    if not track:
                        track = Track(Title=id3.title, Artist=artist)
                        head, tail = os.path.split(newFilePath)
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

        if albumFolder:
            for coverImage in self.inboundCoverImages():
                im = Image.open(coverImage)
                newPath = os.path.join(albumFolder, "cover.jpg")
                im.save(newPath)
                self.printDebug("Copied Cover File [" + newPath + "]")





parser = argparse.ArgumentParser(description='Scan Inbound and Library Folders For Updates.')
parser.add_argument('--verbose', '-v', action='store_true', help='Enable Verbose Print Statements')
parser.add_argument('--showTagsOnly', '-st', action='store_true', help='Only Show Tags for Found Files')
args = parser.parse_args()

scanner = Scanner(args.verbose, args.showTagsOnly)
scanner.scan()