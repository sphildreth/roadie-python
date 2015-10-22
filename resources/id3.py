# Represents ID3 Tag loaded from an MP3 File
import os
import string
import sys
import mutagen
from mutagen.mp3 import MP3
from mutagen.id3 import ID3 as mutagenID3
from mutagen.id3 import ID3NoHeaderError
from mutagen.id3 import ID3, TIT2, TALB, TPE1, TPE2, COMM, USLT, TCOM, TCON, TDRC, TRCK
from resources.logger import Logger
from hsaudiotag import mpeg


class ID3:
    filename = None
    config = None

    def __init__(self,path,config=None):
        self.logger = Logger()
        self.filename = path
        self.config = config
        self._load(path,config)

    def isValid(self):
        try:
            if self.artist and self.year and self.album and self.track and self.title and self.bitrate and self.length > 0:
                return True
            else:
                return False
        except:
            return False

    def info(self):
        return "--- IsValid: [" + str(self.isValid()) + "] Artist [" +  self.artist  + "], Year [" +\
               str(self.year) + "], Album: [" + self.album + "], Disc: [" + str(self.disc) +\
               "] Track [" + str(self.track).zfill(2) + "], Title [" + self.title + "], (" +\
               str(self.bitrate) + "bps::" + str(self.length) + ")"

    def __str__(self):
        return self.artist + "." + str(self.year) + "." + self.album + "." + str(self.track) \
               + "." + self.title + "." + str(self.bitrate) + "." + str(self.length)


    def updateFromRelease(self, Release, TrackRelease):
        try:
            tags = mutagenID3(self.filename)
        except ID3NoHeaderError:
            tags = mutagenID3()
        tags["TIT2"] = TIT2(encoding=3, text= TrackRelease.Track.Title)
        tags["TALB"] = TALB(encoding=3, text=Release.Title)
        tags["TPE2"] = TPE2(encoding=3, text=Release.Artist.Name)
        tags["TPE1"] = TPE1(encoding=3, text=Release.Artist.Name)
        tags["TRCK"] = TRCK(encoding=3, text=str(TrackRelease.TrackNumber))
        if Release.ReleaseDate:
            year = Release.ReleaseDate[:4]
            if year:
                tags["TDRC"] = TDRC(encoding=3, text=year)
        if self.config:
            if 'DoClearComments' in self.config:
                if self.config['DoClearComments'].lower() == "true":
                    tags.delall(u"COMM::'en'")
        tags.save(self.filename)

    def _load(self, filename, config):
        self.dirty = False
        self.artist = ''
        self.album = ''
        self.track = ''
        self.title = ''
        self.year = ''
        self.disc = -1
        self.bitrate = ''
        self.length = -1
        try:
            short_tags = full_tags = mutagen.File(filename)
            comments = []
            if isinstance(full_tags, mutagen.mp3.MP3):
                for key in short_tags:
                    if key[0:4] == 'COMM':
                        if(short_tags[key].desc == ''):
                            comments.append(short_tags[key].text[0])
                short_tags = mutagen.mp3.MP3(filename, ID3 = mutagen.easyid3.EasyID3)
            comments.append('')
            self.album = string.capwords(short_tags.get('album', [''])[0])
            self.artist = string.capwords(short_tags.get('artist', [''])[0])
            self.duration = "%u:%.2d" % (full_tags.info.length / 60, full_tags.info.length % 60)
            trackNumber = short_tags.get('tracknumber', [''])[0]
            self.track = 0
            try:
                if trackNumber and "/" in trackNumber:
                    self.track = int(trackNumber.split("/")[0])
                if trackNumber:
                    self.track = int(trackNumber)
            except:
                pass
            self.length = full_tags.info.length
            self.bitrate = full_tags.info.bitrate
            discNumber = short_tags.get('discnumber', [''])[0]
            self.disc = 0
            try:
                if discNumber and "/" in discNumber:
                    self.disc = int(discNumber.split("/")[0])
                elif discNumber:
                    self.disc = int(discNumber)
            except:
                pass
            self.year = short_tags.get('date', [''])[0]
            if not self.year:
                myfile = mpeg.Mpeg(filename)
                if myfile:
                    self.year = myfile.tag.year[:4]
            self.title = string.capwords(short_tags.get('title', [''])[0])
            if self.title and config:
                if 'TitleReplacements' in config:
                    for rpl in config['TitleReplacements']:
                        for key,val in rpl.items():
                            self.title = self.title.replace(key, val)
                    self.dirty = True
                self.title = string.capwords(self.title)
            if self.title and self.track:
                if self.title.startswith('%02d - ' % self.track):
                    self.title = self.title[5:]
                elif self.title.startswith('%02d ' % self.track):
                    self.title = self.title[3:]
                elif self.title.startswith('- '):
                    self.title = self.title[2:]
                self.title = string.capwords(self.title)
                self.dirty = True
            self.comment = string.capwords(comments[0])
            if self.comment and config:
                if 'DoClearComments' in config:
                    if config['DoClearComments'].lower() == "true":
                        self.comment = None
                        self.dirty = True
            self.genre = ''
            genres = short_tags.get('genre', [''])
            if len(genres) > 0:
                self.genre = genres[0]
            self.size = os.stat(filename).st_size
            self.imageBytes = None
            if full_tags.tags and 'APIC:' in  full_tags.tags:
                self.imageBytes = full_tags.tags._DictProxy__dict['APIC:'].data
        except:
            self.logger.exception()
