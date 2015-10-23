import json
from io import StringIO
from urllib import request, parse

from searchEngines.musicBrainz import MusicBrainz


class ImageSearchResult(object):
    def __init__(self, height, width, url):
        self.height = height
        self.width = width
        self.url = url

    def __str__(self):
        return self.url + " @ " + self.height + "x" + self.width


class ImageSearcher(object):

    def itunesSearchArtistAlbumImages(self, referer, artist, albumTitle):
        if referer.startswith("http://localhost"):
            referer = "http://github.com/sphildreth/roadie"
        url ="http://itunes.apple.com/search?term=" + parse.quote_plus(artist) + "&country=us&limit=25&entity=album"
        rq = request.Request(url=url)
        rq.add_header('Referer', referer)
        result = []
        with request.urlopen(rq) as f:
            try:
                s = StringIO((f.read().decode('utf-8')))
                o = json.load(s)
                for r in o['results']:
                    if r['collectionName'].lower() == albumTitle.lower():
                        result.append(ImageSearchResult(100, 100, r['artworkUrl100']))
            except:
                pass
        return result

    def googleSearchImages(self, referer, requestIp, query):
        if referer.startswith("http://localhost"):
            referer = "http://github.com/sphildreth/roadie"
            requestIp = '192.30.252.128'
        url ="https://ajax.googleapis.com/ajax/services/search/images?v=1.0&rsz=8&q=" + parse.quote_plus(query) + "&userip=" + requestIp
        rq = request.Request(url=url)
        rq.add_header('Referer', referer)
        result = []
        with request.urlopen(rq) as f:
            o = json.load(StringIO((f.read().decode('utf-8'))))
            try:
                for r in o['responseData']['results']:
                    h = int(r['height'])
                    w = int(r['width'])
                    if h and w:
                        result.append(ImageSearchResult(r['height'], r['width'], r['unescapedUrl']))
            except:
                pass
        return result

    def musicbrainzSearchImages(self, musicBrainzId):
        if not musicBrainzId:
            return None
        mb = MusicBrainz()
        r = mb.lookupCoverArt(musicBrainzId)
        if r:
            return ImageSearchResult(0,0,str(r))
        return None

    def getImageBytesForUrl(self, url):
        try:
            s = parse.unquote(url)
            response = request.urlopen(s)
            return response.read()
        except:
            return None