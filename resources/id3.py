import base64
import os
import string


import mutagen
from hsaudiotag import mpeg
from mutagen.id3 import ID3 as mutagenID3, APIC, error
from mutagen.id3 import ID3NoHeaderError
from mutagen.id3 import TIT2, TALB, TPE1, TPE2, TDRC, TRCK
from mutagen.mp3 import MP3

from resources.common import *
from resources.logger import Logger


class ID3(object):
    filename = None
    config = None

    def __init__(self, path, config=None):
        self.logger = Logger()
        self.filename = path
        self.config = config
        self._load(path, config)

    def isValid(self):
        try:
            if self.artist and \
                    self.year and \
                    self.album and \
                    self.track and \
                    self.title and \
                    self.bitrate and \
                            self.length > 0:
                return True
            else:
                return False
        except:
            return False

    def info(self):
        return "--- IsValid: [" + str(self.isValid()) + "] " + \
               "Artist [" + str(self.getArtist()) + "] " + \
               "HasTrackArtist [" + str(self.hasTrackArtist()) + "] " + \
               "Artist (TPE1) [" + str(self.artist) + "], " + \
               "Album Artist (TPE2) [" + str(self.albumArtist) + "], " + \
               "Year [" + str(self.year) + "], " + \
               "Album: [" + str(self.album) + "], " + \
               "Disc: [" + str(self.disc) + "], " + \
               "Track [" + str(self.track).zfill(2) + "], " + \
               "Title [" + str(self.title) + "], " + \
               "(" + str(self.bitrate) + "bps::" + str(self.length) + ")"

    def __str__(self):
        return str(self.artist) + "." + \
               str(self.year) + "." + \
               str(self.album) + "." + \
               str(self.track) + "." + \
               str(self.title) + "." + \
               str(self.bitrate) + "." + \
               str(self.length)

    def setCoverImage(self, image):
        try:
            tags = mutagenID3(self.filename)
        except ID3NoHeaderError:
            tags = mutagenID3()
        if self.config:
            if 'DoClearComments' in self.config:
                if self.config['DoClearComments'].lower() == "true":
                    tags.delall(u"COMM::'en'")
        tags.delall(u"APIC::'en'")
        tags.add(APIC(
                    encoding=3,
                    mime='image/jpeg',
                    type=3,
                    desc=u'Cover',
                    data=image
        ))
        tags.save(self.filename, v2_version=3) # this is for Windows Media Player compatiblity

    def updateFromRelease(self, release, track):
        """
        Update the given Track with loaded values
        :param release: Release
        :param track: Track
        :return:
        """
        try:
            tags = mutagenID3(self.filename)
        except ID3NoHeaderError:
            tags = mutagenID3()
        tags["TIT2"] = TIT2(encoding=3, text=track.title)
        tags["TALB"] = TALB(encoding=3, text=release.title)
        if track.artist:
            tags["TPE2"] = TPE2(encoding=3, text=release.artist.name)
            tags["TPE1"] = TPE1(encoding=3, text=track.artist.name)
        else:
            tags["TPE1"] = TPE1(encoding=3, text=release.artist.name)
        tags["TRCK"] = TRCK(encoding=3, text=str(track.trackNumber))
        if release.releaseDate:
            year = release.releaseDate.strftime('%Y')
            if year:
                tags["TDRC"] = TDRC(encoding=3, text=year)
        if self.config:
            if 'DoClearComments' in self.config:
                if self.config['DoClearComments'].lower() == "true":
                    tags.delall(u"COMM::'en'")
        tags.save(self.filename)

    def getTrackArtist(self):
        """
        Return the artist to use for this track be it Artist ("TPE1") or Album Artist ("TPE2")
        :param self:
        :return: str
        """
        return (self.artist or '').strip()

    def getReleaseArtist(self):
        """
        Return the artist to use for this Release be it Artist ("TPE1") or Album Artist ("TPE2")
        :param self:
        :return: str
        """
        if self.hasTrackArtist():
            return (self.albumArtist or '').strip()
        return (self.artist or '').strip()

    def hasTrackArtist(self):
        # Artist is always set
        artist = (self.artist or '').strip()
        # Album Artist is sometimes set and most of the times when set its the same as the Artist
        albumArtist = (self.albumArtist or '').strip()
        if albumArtist and not isEqual(artist, albumArtist):
            return True
        return False

    def _load(self, filename, config):
        self.dirty = False
        self.artist = ''
        self.albumArtist = ''
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
                        if short_tags[key].desc == '':
                            comments.append(short_tags[key].text[0])
                short_tags = mutagen.mp3.MP3(filename, ID3=mutagen.easyid3.EasyID3)
            comments.append('')
            self.album = string.capwords(short_tags.get('album', [''])[0])
            self.artist = string.capwords(short_tags.get('artist', [''])[0])
            try:
                self.albumArtist = full_tags['TPE2'].text[0]
            except:
                pass
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
                        for key, val in rpl.items():
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
            self.imageBytes = None
            try:
                if full_tags.tags and 'APIC:' in full_tags.tags:
                    self.imageBytes = full_tags.tags._DictProxy__dict['APIC:'].data
            except:
                pass
        except:
            self.logger.exception()
