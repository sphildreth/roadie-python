import os
import sqlite3
import json
from io import StringIO
from urllib import request, parse
from resources.logger import Logger

class ArtistSearchResult(object):

    def __init__(self, id, amgId=None, name=None):
        self.id = id
        self.amgId = amgId
        self.name = name

    def __str__(self):
        return str(self.id) + " [" + self.name + "]"


class ArtistAlbumSearchResult(object):

    def __init__(self, id, title, releaseDate, trackCount, coverUrl):
        self.id = id
        self.title = title
        self.releaseDate = releaseDate
        self.trackCount = trackCount
        self.coverUrl = coverUrl

    def __str__(self):
       return str(self.id) + ": Title [" + self.title + "]: TrackCount [" + str(self.trackCount) + "]: Released [" + self.releaseDate + "]"


class ArtistSearcher(object):

    databaseFilename = "artistSearcher.db"

    def __init__(self, referer=None):
        self.referer = referer
        if not self.referer or self.referer.startswith("http://localhost"):
            self.referer = "http://github.com/sphildreth/roadie"
        self.logger = Logger()

    def __enter__(self):
        self.conn = sqlite3.connect(self.databaseFilename)
        c = self.conn.cursor()
        c.execute("create table if not exists Artists (id integer, amgId integer, name text)")
        c.execute("create index if not exists ArtistName on Artists (name)")
        c.execute("create table if not exists Albums (id integer, artistId integer, title text, releaseDate text, trackCount integer, coverUrl text)")
        self.conn.commit()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()

    def __getArtistFromDB(self,name):
        c = self.conn.cursor()
        sql = 'SELECT * FROM Artists WHERE Name = "' + name + '" COLLATE NOCASE'
        c.execute(sql)
        r = c.fetchone()
      #  self.logger.debug("artistSearcher :: GetArtistFromDB SQL [" + sql + "] Result [" + str(r) + "]")
        if r:
            return ArtistSearchResult(r[0], r[1], r[2])
        else:
            return None

    def __saveArtistToDB(self,artistSearchResult):
        sql = 'INSERT INTO Artists VALUES (' + str(artistSearchResult.id) + ',' + str(artistSearchResult.amgId) + ',"' + artistSearchResult.name + '")'
    #    self.logger.debug("artistSearcher :: SaveArtistToDB SQL [" + sql + "]")
        c = self.conn.cursor()
        c.execute(sql)
        self.conn.commit()


    def __getAlbumsForArtistFromDB(self,artistSearchResult):
        c = self.conn.cursor()
        sql = 'SELECT * FROM Albums WHERE artistId = ' + str(artistSearchResult.id)
        c.execute(sql)
        rs = c.fetchall()
       # self.logger.debug("artistSearcher :: GetAlbumsForArtistFromDB SQL [" + sql + "] Result(s) [" + str(rs) + "]")
        albums = []
        for r in rs:
            albums.append(ArtistAlbumSearchResult(r[0], r[2], r[3], r[4], r[5]))
        return albums

    def __saveAlbumsForArtistToDB(self,artistSearchResult, artistAlbumSearchResults):
        for artistAlbumSearchResult in artistAlbumSearchResults:
            sql = 'INSERT INTO Albums VALUES (' + str(artistAlbumSearchResult.id) + ',' + str(artistSearchResult.id) + ',"' +  artistAlbumSearchResult.title + '","' + artistAlbumSearchResult.releaseDate + '",' + str(artistAlbumSearchResult.trackCount)  + ',"' + artistAlbumSearchResult.coverUrl + '")'
           # self.logger.debug("artistSearcher :: SaveAlbumsForArtistToDB SQL [" + sql + "]")
            c = self.conn.cursor()
            c.execute(sql)
        self.conn.commit()


    def iTunesArtist(self, name):
        self.artistName = name
        try:
            artistSearchResult = self.__getArtistFromDB(name)
            if not artistSearchResult:
                url = "http://itunes.apple.com/search?term=" + parse.quote_plus(self.artistName) + "&entity=musicArtist"
                rq = request.Request(url=url)
                rq.add_header('Referer', self.referer)
                self.logger.debug("artistSearcher :: Performing iTunes Lookup For Artist")
                with request.urlopen(rq) as f:
                    try:
                        s = StringIO((f.read().decode('utf-8')))
                        o = json.load(s)
                        for r in o['results']:
                            artistSearchResult = ArtistSearchResult(r['artistId'], r['amgArtistId'], r['artistName'])
                            self.__saveArtistToDB(artistSearchResult)
                            continue
                    except:
                        self.logger.exception("Getting Artist From iTunes")
                        pass
            return artistSearchResult
        except:
            pass
        return None

    def iTunesAlbumsForArtist(self, iTunesArtist, titleFilter=None):
        albumsSearchResult = self.__getAlbumsForArtistFromDB(ArtistSearchResult(iTunesArtist.id))
        if not albumsSearchResult:
            url = "https://itunes.apple.com/lookup?id=" + str(iTunesArtist.id) + "&entity=album"
            rq = request.Request(url=url)
            rq.add_header('Referer', self.referer)
            albumsSearchResult = []
            self.logger.debug("artistSearcher :: Performing iTunes Lookup For Album(s)")
            with request.urlopen(rq) as f:
                try:
                    s = StringIO((f.read().decode('utf-8')))
                    o = json.load(s)
                    for r in o['results']:
                        try:
                            if 'collectionType' in r and r["collectionType"] == "Album":
                                albumsSearchResult.append(ArtistAlbumSearchResult(r['collectionId'], r['collectionName'], r['releaseDate'], r['trackCount'], r['artworkUrl100']))
                        except:
                            self.logger.exception("Getting Albums From iTunes")
                            pass
                except:
                    pass
            albumsSearchResult = sorted(albumsSearchResult, key=lambda x: x.releaseDate)
            self.__saveAlbumsForArtistToDB(ArtistSearchResult(iTunesArtist.id), albumsSearchResult)
            #if titleFilter and r['collectionName'].lower() == titleFilter.lower():
        return albumsSearchResult
