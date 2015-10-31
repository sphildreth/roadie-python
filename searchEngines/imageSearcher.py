import json
from io import StringIO
from urllib import request, parse
from PIL import Image

from searchEngines.musicBrainz import MusicBrainz


class ImageSearchResult(object):
    def __init__(self, height, width, url):
        self.height = height
        self.width = width
        self.url = url

    def __str__(self):
        return self.url + " @ " + self.height + "x" + self.width


class ImageSearcher(object):
    def __init__(self, referer=None):
        self.referer = referer
        if not self.referer or self.referer.startswith("http://localhost"):
            self.referer = "http://github.com/sphildreth/roadie"

    def itunesSearchArtistAlbumImages(self, artist, albumTitle):
        url = "http://itunes.apple.com/search?term=" + parse.quote_plus(artist) + "&country=us&limit=25&entity=album"
        rq = request.Request(url=url)
        rq.add_header('Referer', self.referer)
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

    def googleSearchImages(self, requestIp, query):
        if self.referer.startswith("http://localhost"):
            requestIp = '192.30.252.128'
        url = "https://ajax.googleapis.com/ajax/services/search/images?v=1.0&rsz=8&q=" + parse.quote_plus(
            query) + "&userip=" + requestIp
        rq = request.Request(url=url)
        rq.add_header('Referer', self.referer)
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

    def getImageBytesForUrl(self, url):
        try:
            req = request.Request(parse.unquote(url))
            req.add_header('Referer', self.referer)
            req.add_header('User-Agent',
                           'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 " + "'
                           '(KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36')
            with request.urlopen(req) as response:
                data = response.read()
            return data
        except:
            return None
