import html
import json
from io import StringIO
from urllib import request, parse

from resources.musicBrainz import MusicBrainz

class ImageSearchResult(object):
    def __init__(self, height, width, url):
        self.height = height
        self.width = width
        self.url = url

    def __str__(self):
        return self.url + " @ " + self.height + "x" + self.width


class ImageSearcher(object):

    def googleSearchImages(self, referer, requestIp, query):
        if referer.startswith("http://localhost"):
            referer = "http://github.com/sphildreth/roadie"
            requestIp = '192.30.252.128'
        url ="https://ajax.googleapis.com/ajax/services/search/images?v=1.0&q=" + parse.quote_plus(query) + "&userip=" + requestIp
        rq = request.Request(url=url)
        rq.add_header('Referer', referer)
        result = []
        with request.urlopen(rq) as f:
            o = json.load(StringIO((f.read().decode('utf-8'))))
            for r in o['responseData']['results']:
                result.append(ImageSearchResult(r['height'], r['width'], r['unescapedUrl']))
        return result

    def musicbrainzSearchImages(self, musicBrainzId):
        if not musicBrainzId:
            return None
        mb = MusicBrainz()
        r = mb.lookupCoverArt(musicBrainzId)
        return ImageSearchResult(0,0,r)

    def getImageBytesForUrl(self, url):
        s = parse.unquote(url)
        response = request.urlopen(s)
        return response.read()