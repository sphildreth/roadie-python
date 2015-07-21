# Represents ID3 Tag loaded from an MP3 File
import os
import sys
import mutagen
from mutagen.mp3 import MP3
from utility import Utility


class ID3:

    def __init__(self,path):
        self._load(path)

    def isValid(self):
        try:
            if self.artist and self.year and self.album and self.track and self.title and self.bitrate and self.length:
                return True
            else:
                return False
        except:
            return False

    def __str__(self):
        return self.artist + "." + str(self.year) + "." + self.album  + "." + str(self.track) + "." + self.title + "." + str(self.bitrate) + "." + str(self.length)

    def _load(self, filename):
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
            self.album = short_tags.get('album', [''])[0].strip().title()
            self.artist = short_tags.get('artist', [''])[0].strip().title()
            self.duration = "%u:%.2d" % (full_tags.info.length / 60, full_tags.info.length % 60)
            trackNumber = short_tags.get('tracknumber', [''])[0]
            self.track = 0
            try:
                if trackNumber and "/" in trackNumber:
                    self.track = int(trackNumber.split("/")[0])
                elif trackNumber:
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
            self.title = short_tags.get('title', [''])[0].strip().title()
            self.comment = comments[0].title()
            self.genre = ''
            genres = short_tags.get('genre', [''])
            if len(genres) > 0:
                self.genre = genres[0]
            self.size = os.stat(filename).st_size
            self.imageBytes = None
            if full_tags.tags and 'APIC:' in  full_tags.tags:
                self.imageBytes = full_tags.tags._DictProxy__dict['APIC:'].data
        except:
            Utility.PrintException()
            return None
