import json
import threading
import hashlib

from queue import Queue
from io import StringIO
from urllib import request, parse

from resources.common import *
from searchEngines.searchEngineBase import SearchEngineBase, ThreadData
from searchEngines.models.Artist import Artist
from searchEngines.models.Image import Image
from searchEngines.models.Release import Release
from searchEngines.models.ReleaseMedia import ReleaseMedia
from searchEngines.models.Track import Track


class LastFM(SearchEngineBase):
    API_KEY = "a31dd32179375f9e332b89f8b9e38fc5"
    API_SECRET = "35b3684601b2ecf9c0c0c1cfda28159e"

    IsActive = True

    threadDataType = "lastFm"
    lock = threading.Lock()
    que = Queue()

    cache = dict()

    artistReleasesThreaded = []

    def __init__(self, referer=None):
        self.baseUrl = "http://ws.audioscrobbler.com/2.0/?api_key=" + self.API_KEY + "&format=json&method="
        SearchEngineBase.__init__(self, referer)

    def lookupArtist(self, name):
        try:
            artist = None
            url = self.baseUrl + "artist.getInfo&artist=" + parse.quote_plus(name)
            rq = request.Request(url=url)
            rq.add_header('Referer', self.referer)
            self.logger.debug("Performing LastFM Lookup For Artist")
            with request.urlopen(rq) as f:
                try:
                    s = StringIO((f.read().decode('utf-8')))
                    o = json.load(s)
                    if 'artist' in o and o['artist']:
                        r = o['artist']
                        artist = Artist(name=r['name'])
                        artist.images = []
                        if 'mbid' in r:
                            artist.musicBrainzId = r['mbid']
                        if 'image' in r:
                            images = r['image']
                            if images:
                                for image in images:
                                    if isEqual(image['size'], 'extralarge'):
                                        artist.images.append(Image(url=image['#text']))
                        if 'tags' in r:
                            tags = r['tags']
                            if tags:
                                artist.tags = []
                                for tags in r['tags']['tag']:
                                    tag = tags['name']
                                    if not isInList(artist.tags, tag):
                                        artist.tags.append(tag)
                        if 'bio' in r:
                            bio = r['bio']
                            if bio:
                                artist.bioContent = bio['content']
                except:
                    self.logger.exception("LastFM: Error In LookupArtist")
                    pass
                    #  if artist:
                    #       print(artist.info())
            return artist
        except:
            self.logger.exception("LastFM: Error In LookupArtist")
            pass
        return None

    def searchForRelease(self, artist, title):
        artistPart = "&artist=" + parse.quote_plus(artist.name)
        url = self.baseUrl + "album.getInfo" + artistPart + "&album=" + parse.quote_plus(title)
        self.logger.debug("Performing LastFM Lookup For Album [" + title + "]")
        return self._fetchFromUrl(url)

    def threader(self):
        while True:
            threadData = self.que.get()
            if threadData.threadDataType == self.threadDataType:
                self.threaderLookupRelease(threadData.data)
                self.que.task_done()

    def threaderLookupRelease(self, url):
        release = self._fetchFromUrl(url)
        if release:
            with self.lock:
                if release in self.artistReleasesThreaded:
                    for r in self.artistReleasesThreaded:
                        if r == release:
                            r.mergeWithRelease(release)
                else:
                    self.artistReleasesThreaded.append(release)

    def lookupReleasesForMusicBrainzIdList(self, artist, mbIdList):
        """
        This is because there is no way to ge all the releases from an Artist via LastFM and their top albums query
        contains releases not by the given artist.
        :param mbIdList:
        :return:
        """
        cacheKey = hashlib.sha1((artist.roadieId + str(mbIdList)).encode('utf-8')).hexdigest()
        if cacheKey not in self.cache:
            self.artistReleasesThreaded = []
            for x in range(self.threadCount):
                t = threading.Thread(target=self.threader)
                t.daemon = True
                t.start()

            for musicBrainzId in mbIdList:
                url = self.baseUrl + "album.getInfo&mbid=" + musicBrainzId
                self.logger.debug("Performing LastFM Lookup For Album MbId [" + musicBrainzId + "]")

                self.que.put(ThreadData(self.threadDataType, url))

            self.que.join()
            self.cache[cacheKey] = self.artistReleasesThreaded
        else:
            self.logger.debug(
                "Found Artist: roadieId [" + artist.roadieId + "] name [" + artist.name + "] in LastFM Cache.")
        return self.cache[cacheKey]

    def _fetchFromUrl(self, url):
        if not url:
            return None
        try:
            release = None
            rq = request.Request(url=url)
            rq.add_header('Referer', self.referer)
            with request.urlopen(rq) as f:
                mediaTrackCount = 0
                try:
                    s = StringIO((f.read().decode('utf-8')))
                    o = json.load(s)
                    if 'album' not in o:
                        return None
                    r = o['album']
                    tracks = r['tracks']
                    images = r['image']
                    coverUrl = None
                    if images:
                        for image in images:
                            if isEqual(image['size'], 'extralarge'):
                                coverUrl = image['#text']
                    release = Release(title=r['name'])
                    release.trackCount = len(tracks)
                    release.coverUrl = coverUrl
                    if 'id' in r and r['id']:
                        release.lastFMId = r['id']
                    tags = r['tags']
                    if tags:
                        release.tags = []
                        for tag in r['tags']['tag']:
                            tagName = tag['name']
                            if not isInList(release.tags, tagName):
                                release.tags.append(tagName)
                    if tracks:
                        media = ReleaseMedia(releaseMediaNumber=1)
                        media.tracks = []
                        for t in tracks['track']:
                            track = Track(title=t['name'])
                            track.duration = t['duration']
                            track.trackNumber = t['@attr']['rank']
                            if not ([t for t in media.tracks if t.trackNumber == track.trackNumber]):
                                media.tracks.append(track)
                                mediaTrackCount += 1
                        release.media = []
                        release.media.append(media)
                        release.mediaCount = 1
                        release.trackCount = len(media.tracks)
                    if 'wiki' in r and r['wiki']:
                        if 'summary' in r['wiki'] and r['wiki']['summary']:
                            release.lastFMSummary = r['wiki']['summary']
                    if not release.alternateNames:
                        release.alternateNames = []
                    cleanedTitle = createCleanedName(release.title)
                    if cleanedTitle not in release.alternateNames and cleanedTitle != release.title:
                        release.alternateNames.append(cleanedTitle)
                    # Not Valid
                    if mediaTrackCount < 1:
                        release = None
                    return release
                except:
                    self.logger.exception("LastFM: Error In SearchForRelease")
                    pass
            return release
        except:
            self.logger.exception("LastFM: Error In SearchForRelease")
            pass
        return None

# a = LastFM()
# artist = a.lookupArtist('Men At Work')
# release = a.searchForRelease(artist, "Cargo")
# print(artist.info())
