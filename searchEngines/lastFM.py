import json
from io import StringIO
from urllib import request, parse

from searchEngines.searchEngineBase import SearchEngineBase
from resources.models.Artist import Artist
from resources.models.Image import Image
from resources.models.Release import Release
from resources.models.ReleaseMedia import ReleaseMedia
from resources.models.Track import Track


class LastFM(SearchEngineBase):
    API_KEY = "a31dd32179375f9e332b89f8b9e38fc5"
    API_SECRET = "35b3684601b2ecf9c0c0c1cfda28159e"

    IsActive = True

    def __init__(self, referer=None):
        self.baseUrl = "http://ws.audioscrobbler.com/2.0/?api_key=" + self.API_KEY + "&format=json&method="
        SearchEngineBase.__init__(self, referer)

    def lookupArtist(self, name):
        try:
            artist = None
            url = self.baseUrl + "artist.getInfo&artist=" + parse.quote_plus(name)
            rq = request.Request(url=url)
            rq.add_header('Referer', self.referer)
            self.logger.debug("artistSearcher :: Performing LastFM Lookup For Artist")
            with request.urlopen(rq) as f:
                try:
                    s = StringIO((f.read().decode('utf-8')))
                    o = json.load(s)
                    r = o['artist']
                    artist = Artist(name=r['name'])
                    artist.images = []
                    artist.musicBrainzId = r['mbid']
                    images = r['image']
                    if images:
                        for image in images:
                            if image['size'] == 'extralarge':
                                artist.images.append(Image(url=image['#text']))
                    tags = r['tags']
                    if tags:
                        artist.tags = []
                        for tag in r['tags']['tag']:
                            artist.tags.append(tag['name'])
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

    def searchForRelease(self, artistSearchResult, title):
        try:
            release = None
            artistPart = "&artist=" + parse.quote_plus(artistSearchResult.name)
            url = self.baseUrl + "album.getInfo" + artistPart + "&album=" + parse.quote_plus(title)
            rq = request.Request(url=url)
            rq.add_header('Referer', self.referer)
            self.logger.debug("artistSearcher :: Performing LastFM Lookup For Album")
            with request.urlopen(rq) as f:
                try:
                    s = StringIO((f.read().decode('utf-8')))
                    o = json.load(s)
                    r = o['album']
                    tracks = r['tracks']
                    images = r['image']
                    coverUrl = None
                    if images:
                        for image in images:
                            if image['size'] == 'extralarge':
                                coverUrl = image['#text']
                    release = Release(title=r['name'], trackCount=len(tracks), coverUrl=coverUrl)
                    tags = r['tags']
                    if tags:
                        release.tags = []
                        for tag in r['tags']['tag']:
                            release.tags.append(tag['name'])
                    if tracks:
                        media = ReleaseMedia(releaseMediaNumber=1)
                        media.tracks = []
                        for t in tracks['track']:
                            track = Track(title=t['name'])
                            track.duration = t['duration']
                            track.trackNumber = t['@attr']['rank']
                            if not filter(lambda x: x.trackNumber == track.trackNumber, media.tracks):
                                media.tracks.append(track)
                        release.media = []
                        release.media.append(media)
                        release.trackCount = len(media.tracks)
                    return release
                except:
                    pass
            return release
        except:
            self.logger.exception("LastFM: Error In SearchForRelease")
            pass
        return None
