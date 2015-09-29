import json
from io import StringIO
from urllib import request, parse

from searchEngines.searchEngineBase import SearchEngineBase
from searchEngines.searchResult import *


class LastFM(SearchEngineBase):
    API_KEY = "a31dd32179375f9e332b89f8b9e38fc5"
    API_SECRET = "35b3684601b2ecf9c0c0c1cfda28159e"

    IsActive = True

    def __init__(self, referer=None):
        self.baseUrl = "http://ws.audioscrobbler.com/2.0/?api_key=" + self.API_KEY + "&format=json&method="
        SearchEngineBase.__init__(self, referer)

    def lookupArtist(self, name):
        try:
            artistSearchResult = None
            url = self.baseUrl + "artist.getInfo&artist=" + parse.quote_plus(name)
            rq = request.Request(url=url)
            rq.add_header('Referer', self.referer)
            self.logger.debug("artistSearcher :: Performing LastFM Lookup For Artist")
            with request.urlopen(rq) as f:
                try:
                    s = StringIO((f.read().decode('utf-8')))
                    o = json.load(s)
                    r = o['artist']
                    artistSearchResult = ArtistSearchResult(r['name'])
                    artistSearchResult.musicBrainzId = r['mbid']
                    images = r['image']
                    if images:
                        for image in images:
                            if image['size'] == 'extralarge':
                                artistSearchResult.imageUrl = image['#text']
                    tags = r['tags']
                    if tags:
                        artistSearchResult.tags = []
                        for tag in r['tags']['tag']:
                            artistSearchResult.tags.append(tag['name'])
                    bio = r['bio']
                    if bio:
                        artistSearchResult.bioContent = bio['content']
                    return artistSearchResult
                except:
                    pass
            return artistSearchResult
        except:
            self.logger.exception("LastFM: Error In LookupArtist")
            pass
        return None

    def searchForRelease(self, artistSearchResult, title):
        try:
            albumSearchResult = None
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
                    albumSearchResult = ArtistReleaseSearchResult(r['name'], None, len(tracks), coverUrl)
                    tags = r['tags']
                    if tags:
                        albumSearchResult.tags = []
                        for tag in r['tags']['tag']:
                            albumSearchResult.tags.append(tag['name'])
                    if tracks:
                        albumSearchResult.tracks = dict()
                        for t in tracks['track']:
                            track = ArtistReleaseTrackSearchResult(t['name'])
                            track.duration = t['duration']
                            track.trackNumber = t['@attr']['rank']
                            if track.trackNumber not in albumSearchResult.tracks:
                                albumSearchResult.tracks[track.trackNumber] = track
                        albumSearchResult.trackCount = len(albumSearchResult.tracks)
                    return albumSearchResult
                except:
                    pass
            return albumSearchResult
        except:
            self.logger.exception("LastFM: Error In SearchForRelease")
            pass
        return None
