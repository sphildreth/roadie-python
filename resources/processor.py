# Process that looks at and processes files/directories in inbound folder
# --- Find or Make Artist For File
# --- Find or Make Release For File
# --- Determine if File Should Be Moved if so move
# --- Each folder call scanner
# --- If folder is empty delete
import arrow
import linecache
import io
import os
import random
import shutil
import json
import hashlib
from PIL import Image
from dateutil.parser import *
from shutil import move
from mongoengine import connect
from resources.models import Artist, ArtistType, Label, Release, ReleaseLabel, Track, TrackRelease
from resources.musicBrainz import MusicBrainz
from resources.id3 import ID3
from resources.scanner import Scanner
from resources.convertor import Convertor
from resources.logger import Logger
from resources.processingBase import ProcessorBase

class Processor(ProcessorBase):

    def __init__(self, readOnly, dontDeleteInboundFolders):
        d = os.path.dirname(os.path.realpath(__file__)).split(os.sep)
        path = os.path.join(os.sep.join(d[:-1]), "settings.json")
        with open(path, "r") as rf:
            config = json.load(rf)
        self.InboundFolder = config['ROADIE_INBOUND_FOLDER']
        self.LibraryFolder = config['ROADIE_LIBRARY_FOLDER']
        # TODO if set then process music files; like clear comments
        self.processingOptions = config['ROADIE_PROCESSING']
        self.dbName = config['MONGODB_SETTINGS']['DB']
        self.host = config['MONGODB_SETTINGS']['host']
        self.thumbnailSize = config['ROADIE_THUMBNAILS']['Height'], config['ROADIE_THUMBNAILS']['Width']
        self.readOnly = readOnly or False
        self.dontDeleteInboundFolders = dontDeleteInboundFolders or False
        self.logger = Logger()

    def releaseCoverImages(self, folder):
        try:
            image_filter = ['.jpg', '.jpeg', '.bmp', '.png', '.gif']
            cover_filter = ['cover', 'front']
            for r, d, f in os.walk(folder):
                for file in f:
                    root, file = os.path.split(file)
                    root, ext = os.path.splitext(file)
                    if ext.lower() in image_filter and root.lower() in cover_filter:
                        yield os.path.join(r, file)
        except:
            self.logger.exception()


    def shouldDeleteFolder(self, mp3Folder, newMp3Filename):
        if self.dontDeleteInboundFolders:
            return False

        if self.readOnly:
            return False

        # Is folder to delete empty?
        if not os.listdir(mp3Folder):
            return True

        return False

    # Determine if the found file should be moved into the library; check for existing and see if better
    def shouldMoveToLibrary(self, artist, artistId, id3, mp3):
        try:
            fileFolderLibPath = os.path.join(self.artistFolder(artist), self.albumFolder(artist, id3.year, id3.album))
            os.makedirs(fileFolderLibPath, exist_ok=True)
            fullFileLibPath = os.path.join(fileFolderLibPath, self.makeFileFriendly(self.trackName(id3.track, id3.title)))
            if not os.path.isfile(fullFileLibPath):
                # Does not exist copy it over
                return True
            else:
                # Does exist see if the one being copied is 'better' then the existing
                existingId3 = ID3(fullFileLibPath, self.processingOptions)
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
            self.logger.exception()
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
            newFilename = os.path.join(self.artistFolder(artist), self.albumFolder(artist, id3.year, id3.album), self.trackName(id3.track, id3.title))
            isMp3File = os.path.isfile(mp3)
            isNewFilenameFile = os.path.isfile(newFilename)
            # If it already exists delete it as the shouldMove function determines if the file should be overwritten or not
            if isMp3File and isNewFilenameFile and not os.path.samefile(mp3, newFilename):
                try:
                    os.remove(newFilename)
                    self.logger.warn("x Deleting Existing [" + newFilename + "]")
                except OSError:
                    pass

            if isMp3File and (mp3 != newFilename):
                try:
                    move(mp3, newFilename)
                    self.logger.info("= Moving [" + mp3 + "] => [" + newFilename + "]")
                except OSError:
                    pass

            return newFilename
        except:
            self.logger.exception()
            return None

    def process(self, **kwargs):
        """
        Process inbound folder using the passed folder

        """
        inboundFolder = kwargs.pop('folder', self.InboundFolder)
        self.logger.info("Processing Inbound Folder [" + inboundFolder + "]")
        connect(self.dbName, host=self.host)
        mb = MusicBrainz()
        scanner = Scanner(self.readOnly)
        startTime = arrow.utcnow().datetime
        newMp3Folder = None
        lastID3Artist = None
        lastID3Album = None
        artist = None
        release = None

        # Get all the folder in the InboundFolder
        for mp3Folder in self.allDirectoriesInDirectory(inboundFolder):
            foundMp3Files = 0

            # Do any conversions
            if not self.readOnly:
                Convertor(mp3Folder)

            # Delete any empty folder if enabled
            if not os.listdir(mp3Folder) and not self.dontDeleteInboundFolders:
                try:
                    self.logger.warn("X Deleted Empty Folder [" + mp3Folder + "]")
                    if not self.readOnly:
                        os.rmdir(mp3Folder)
                except OSError:
                    self.logger.error("Error Deleting [" + mp3Folder + "]")
                continue

            # Get all the MP3 files in the Folder and process
            for rootFolder, mp3 in self.folderMp3Files(mp3Folder):
                self.logger.debug("Processing MP3 File [" + mp3 + "]...")
                id3 = ID3(mp3, self.processingOptions)
                if id3 != None:
                    self.logger.debug("ID3 Info [" + id3.info() + "]");
                    if not id3.isValid():
                        self.logger.warn("! Track Has Invalid or Missing ID3 Tags [" + mp3 + "]")
                    else:
                        foundMp3Files += 1
                        # Get Artist
                        if lastID3Artist != id3.artist:
                            artist = None
                        if not artist:
                            lastID3Artist = id3.artist
                            # get artist by ID3 Tag Name
                            artist = Artist.objects(Name__iexact=id3.artist).first()
                            # If not found get by artists by alternate names
                            if not artist:
                                artist = Artist.objects(AlternateNames__iexact=id3.artist).first()
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
                                ended = mbArtist['life-span']['ended']
                                if ended != "false":
                                    ended = None
                                    if 'life-span' in mbArtist:
                                        if 'end' in mbArtist['life-span']:
                                            ended = parse(mbArtist['life-span']['end'])
                                    artist.EndDate = ended
                                artistType = None
                                if 'type' in mbArtist:
                                    mbArtistType = mbArtist['type']
                                    artistType = ArtistType.objects(Name__iexact=mbArtistType).first()
                                    if not artistType:
                                        self.logger.warn("Unable To Find Artist Type [" + mbArtistType + "]")
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
                            if os.path.exists(artistFile):
                                ba = self.readImageThumbnailBytesFromFile(artistFile)
                            if ba:
                                artist.Thumbnail.new_file()
                                artist.Thumbnail.write(ba)
                                artist.Thumbnail.close()
                            # Save The Artist
                            if not self.readOnly:
                                Artist.save(artist)
                            self.logger.info("+ Added Artist Name [" + artist.Name + "]")
                        # Cannot continue past here if read only as object refer to DB objects must be saved
                        if self.readOnly:
                            continue
                        # Get the Release
                        if lastID3Album != id3.album:
                            release = None
                        if not release:
                            lastID3Album = id3.album
                            release = Release.objects(Title__iexact=id3.album, Artist=artist).first()
                        if not release:
                            release = Release.objects(AlternateNames__iexact=id3.album, Artist=artist).first()
                        if not release:
                            # Release not found create
                            release = Release(Title=id3.album, Artist=artist, ReleaseDate="---")
                            release.Random = random.randint(1, 1000000)
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
                                                    if not self.readOnly:
                                                        Label.save(label)
                                                    self.logger.info("+ Added Label Name [" + label.Name + "]")
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
                                try:
                                    img = Image.open(io.BytesIO(id3.imageBytes)).convert('RGB')
                                    img.thumbnail(self.thumbnailSize)
                                    b = io.BytesIO()
                                    img.save(b, "JPEG")
                                    ba = b.getvalue()
                                except:
                                    pass
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
                                        try:
                                            img = Image.open(io.BytesIO(coverArtBytes))
                                            img.thumbnail(self.thumbnailSize)
                                            b = io.BytesIO()
                                            img.save(b, "JPEG")
                                            ba = b.getvalue()
                                        except:
                                            pass
                            # If Cover Art Thumbnail bytes found then set to Release Thumbnail
                            if ba:
                                release.Thumbnail.new_file()
                                release.Thumbnail.write(ba)
                                release.Thumbnail.close()
                            if not self.readOnly:
                                Release.save(release)
                            self.logger.info("+ Added Release: Title [" + release.Title + "]")
                        if self.shouldMoveToLibrary(artist, artist.id, id3, mp3):
                            newMp3 = self.moveToLibrary(artist, id3, mp3)
                            head, tail = os.path.split(newMp3)
                            newMp3Folder = head

            if artist and release:
                if newMp3Folder:
                    for coverImage in self.releaseCoverImages(mp3Folder):
                        im = Image.open(coverImage).convert('RGB')
                        newPath = os.path.join(newMp3Folder, "cover.jpg")
                        if not self.readOnly:
                            im.save(newPath)
                        self.logger.info("+ Copied Cover File [" + coverImage + "] => [" + newPath + "]")
                    scanner.scan(newMp3Folder, artist, release)
                else:
                    scanner.scan(mp3Folder, artist, release)

            if not self.readOnly and artist and release and id3:
                if self.shouldDeleteFolder(mp3Folder, newMp3Folder):
                    try:
                        shutil.rmtree(mp3Folder)
                        self.logger.debug("x Deleted Processed Folder [" + mp3Folder + "]")
                    except OSError:
                        pass

            self.logger.debug("Processed Folder [" + mp3Folder + "] Processed [" + str(foundMp3Files) + "] MP3 Files")

        elapsedTime = arrow.utcnow().datetime - startTime
        self.logger.info("Processing Complete. Elapsed Time [" + str(elapsedTime) + "]")
