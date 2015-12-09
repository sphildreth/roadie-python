import json
import re
from io import StringIO
from urllib import request, parse

from searchEngines.bing import imageSearch


class ImageSearchResult(object):
    def __init__(self, height, width, url):
        self.height = height
        self.width = width
        self.url = url

    def __str__(self):
        return self.url + " @ " + self.height + "x" + self.width


class ImageSearcher(object):

    regex = re.compile(
            r'^(?:http|ftp)s?://' # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
            r'localhost|' #localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
            r'(?::\d+)?' # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    def __init__(self, requestIp=None, referer=None):
        self.referer = referer
        if not self.referer or self.referer.startswith("http://localhost"):
            self.referer = "http://github.com/sphildreth/roadie"
        if self.referer.startswith("http://localhost") or (not requestIp or requestIp == "::1"):
            self.requestIp = '192.30.252.128'

    def searchForReleaseImages(self, artistName, releaseTitle, query=None):

        result = []
        if query and self.regex.match(parse.unquote(query)):
            result.append(ImageSearchResult(0, 0, parse.unquote(query)))
            return result

        try:
            bingResult = self.bingSearchImages(artistName + " " + releaseTitle)
            if bingResult:
                for br in bingResult:
                    result.append(br)
        except:
            pass

        try:
            it = self.itunesSearchArtistReleaseImages(artistName, releaseTitle)
            if it:
                for i in it:
                    result.append(i)
        except:
            pass

        return result

    def itunesSearchArtistReleaseImages(self, artistName, releaseTitle):
        url = "http://itunes.apple.com/search?term=" + parse.quote_plus(artistName) + "&country=us&limit=25&entity=album"
        rq = request.Request(url=url)
        rq.add_header('Referer', self.referer)
        result = []
        with request.urlopen(rq) as f:
            try:
                s = StringIO((f.read().decode('utf-8')))
                o = json.load(s)
                for r in o['results']:
                    if r['collectionName'].lower() == releaseTitle.lower():
                        result.append(ImageSearchResult(100, 100, r['artworkUrl100']))
            except:
                pass
        return result

    def bingSearchImages(self, query):
        result = []
        bingResults = imageSearch(query)
        if bingResults:
            try:
                for bingResult in bingResults:
                    h = int(bingResult['Height'])
                    w = int(bingResult['Width'])
                    if h and w:
                        result.append(ImageSearchResult(h, w, bingResult['MediaUrl']))
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

# s = ImageSearcher(None)
# i = s.searchForReleaseImages("Men At Work", "Cargo")
# print(i)
