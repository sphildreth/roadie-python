import os
import sqlite3
import json
import string
from io import StringIO
from urllib import request, parse
from resources.logger import Logger
from resources.musicBrainz import MusicBrainz

class ArtistSearchResult(object):

    def __init__(self, name):
        self.name = name
        self.sortName = None
        self.id = None
        self.musicBrainzId = None
        self.iTunesId = None
        self.amgId = None
        self.beginDate = None
        self.endDate = None
        self.artistType = None
        self.imageUrl = None
        self.tags = []
        self.alternateNames = []

    def __str__(self):
        return "Id [" + str(self.id) + "], MusicBrainzId [" + str(self.musicBrainzId) + "], " + \
               "AlternateNames [" + str(len(self.alternateNames or [])) + "], Tags [" + str(len(self.tags or [])) + \
               "], ITunesId [" + str(self.iTunesId) + "], AmgId [" + str(self.amgId) + "], Name [" + str(self.name) + "]"


class ArtistReleaseSearchResult(object):

    def __init__(self, title, releaseDate, trackCount, coverUrl):
        self.title = title
        self.releaseDate = releaseDate
        self.trackCount = trackCount
        self.coverUrl = coverUrl
        self.id = None
        self.musicBrainzId = None
        self.iTunesId = None

    def __str__(self):
       return "Id [" + str(self.id) + ", MusicBrainzId [" + str(self.musicBrainzId) + "], ITunesId [" + str(self.iTunesId) + \
              "], ReleaseDate [" + str(self.releaseDate) + "], TrackCount [" + str(self.trackCount) + "], Title [" + str(self.title) + "]"


class ArtistSearcher(object):

    databaseFilename = "artistsReference.db"

    def __init__(self, referer=None):
        self.referer = referer
        if not self.referer or self.referer.startswith("http://localhost"):
            self.referer = "http://github.com/sphildreth/roadie"
        self.logger = Logger()

    def __enter__(self):
        self.conn = sqlite3.connect(self.databaseFilename)
        c = self.conn.cursor()
        c.execute("create table if not exists Artists (id INTEGER PRIMARY KEY, musicBrainzId text, iTunesId integer, amgId integer, beginDate text, endDate text, artistType text, imageUrl text, name text, sortName text)")
        c.execute("create index if not exists ArtistName on Artists (name)")
        c.execute("create table if not exists ArtistTags (id INTEGER PRIMARY KEY, artistId integer, tag text)")
        c.execute("create index if not exists ArtistTagsArtistId on ArtistTags (artistId)")
        c.execute("create table if not exists ArtistAlternateNames (id INTEGER PRIMARY KEY, artistId integer, name text)")
        c.execute("create index if not exists ArtistAlternateNamesArtistId on ArtistAlternateNames (artistId)")
        c.execute("create table if not exists Releases (id INTEGER PRIMARY KEY, artistId integer, musicBrainzId text, iTunesId integer, title text, releaseDate text, trackCount integer, coverUrl text)")
        c.execute("create index if not exists ReleasesArtistId on Releases (artistId)")
        self.conn.commit()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()

    def __getArtistFromDB(self,name):
        c = self.conn.cursor()
        sql = 'SELECT * FROM Artists WHERE Name = "' + name + '" COLLATE NOCASE'
        c.execute(sql)
        r = c.fetchone()
        if r:
            re = ArtistSearchResult(r[8])
            re.id = r[0]
            re.musicBrainzId = r[1]
            re.iTunesId = r[2]
            re.amgId = r[3]
            re.sortName = r[9]
            re.beginDate = r[4]
            re.endDate = r[5]
            re.artistType = r[6]
            re.imageUrl = r[7]

            re.tags = None
            re.alternateNames = None

            return re
        else:
            return None

    def __saveArtistToDB(self,artistSearchResult):
        c = self.conn.cursor()
        mbId = "null"
        if artistSearchResult.musicBrainzId:
            mbId = '"' + artistSearchResult.musicBrainzId + '"'
        sql = 'INSERT INTO Artists (musicBrainzId, iTunesId, amgId, beginDate, endDate, artistType, imageUrl, name, sortName) VALUES (' + \
              mbId + ',' + \
              str(artistSearchResult.iTunesId) + ',' + \
              str(artistSearchResult.amgId) + ',"' + \
              str(artistSearchResult.beginDate) + '","' + \
              str(artistSearchResult.endDate) + '","' + \
              str(artistSearchResult.artistType) + '","' + \
              str(artistSearchResult.imageUrl) + '","' + \
              str(artistSearchResult.name) + '","' + \
              str(artistSearchResult.sortName) + '")'
        c.execute(sql)
        self.conn.commit()

    def __saveArtistTagsToDB(self,artistSearchResult):
        c = self.conn.cursor()
        if artistSearchResult.tags:
            for tag in artistSearchResult.tags:
                if tag:
                    sql = 'INSERT INTO ArtistTags (artistId, tag) VALUES (' + str(artistSearchResult.id) + ',"' + str(tag) + ',")'
                    c.execute(sql)
        self.conn.commit()

    def __saveArtistAlternateNamesToDB(self,artistSearchResult):
        c = self.conn.cursor()
        if artistSearchResult.alternateNames:
            for alternateName in artistSearchResult.alternateNames:
                if alternateName:
                    sql = 'INSERT INTO ArtistAlternateNames (artistId, name) VALUES (' + str(artistSearchResult.id) + ',"' + str(alternateName) + ',")'
                    c.execute(sql)
        self.conn.commit()


    def __getAlbumsForArtistFromDB(self,artistSearchResult):
        c = self.conn.cursor()
        sql = 'SELECT * FROM Releases WHERE artistId = ' + str(artistSearchResult.id)
        c.execute(sql)
        rs = c.fetchall()
        releases = []
        for r in rs:
            release = ArtistReleaseSearchResult(r[4], r[5], r[6], r[7])
            release.id = r[0]
            release.musicBrainzId = r[2]
            release.iTunesId = r[3]
            releases.append(release)
        return releases


    def __saveReleasesForArtistToDB(self,artistSearchResult, ArtistReleaseSearchResults):
        c = self.conn.cursor()
        for artistReleaseSearchResult in ArtistReleaseSearchResults:
            sql = 'INSERT INTO Releases (artistId, musicBrainzId, iTunesId, title, releaseDate, trackCount, coverUrl) VALUES (' + \
                  str(artistSearchResult.id) + ',"' + \
                  str(artistReleaseSearchResult.musicBrainzId) + '",' +  \
                  str(artistReleaseSearchResult.iTunesId) + ',"' +  \
                  str(artistReleaseSearchResult.title) + '","' + \
                  str(artistReleaseSearchResult.releaseDate) + '",' + \
                  str(artistReleaseSearchResult.trackCount)  + ',"' + \
                  str(artistReleaseSearchResult.coverUrl) + '")'
            c.execute(sql)
        self.conn.commit()


    def searchForArtist(self, name):
        artistSearchResult = self.__getArtistFromDB(name)
        if not artistSearchResult:
            artistSearchResult = ArtistSearchResult(name)
            mbArtist = self.__musicBrainzArtist(name)
            if mbArtist:
                artistSearchResult.musicBrainzId = mbArtist.musicBrainzId
                artistSearchResult.sortName = mbArtist.sortName
                artistSearchResult.beginDate = mbArtist.beginDate
                artistSearchResult.endDate = mbArtist.endDate
                artistSearchResult.artistType = mbArtist.artistType
            itArtist = self.__iTunesArtist(name)
            if itArtist:
                artistSearchResult.name = itArtist.name
                artistSearchResult.iTunesId = itArtist.iTunesId
                artistSearchResult.amgId = itArtist.amgId
            self.__saveArtistToDB(artistSearchResult)
            artistSearchResult = self.__getArtistFromDB(name)
            if mbArtist:
                artistSearchResult.tags = mbArtist.tags
                artistSearchResult.alternateNames = mbArtist.alternateNames
                self.__saveArtistTagsToDB(artistSearchResult)
                self.__saveArtistAlternateNamesToDB(artistSearchResult)
            artistSearchResult = self.__getArtistFromDB(name)
        return artistSearchResult


    def __musicBrainzArtist(self, name):
        try:
            artistSearchResult = None
            mb = MusicBrainz()
            mbArtist = mb.lookupArtist(name)
            if mbArtist:
                artistSearchResult = ArtistSearchResult(name)
                artistSearchResult.musicBrainzId = mbArtist['id']
                artistSearchResult.sortName = mbArtist['sort-name']
                if 'life-span' in mbArtist:
                    if 'begin' in mbArtist['life-span']:
                        artistSearchResult.beginDate = mbArtist['life-span']['begin']
                    if 'end' in mbArtist['life-span']:
                        artistSearchResult.endDate = mbArtist['life-span']['end']
                if 'type' in mbArtist:
                    artistSearchResult.artistType = mbArtist['type']
                artistSearchResult.tags = []
                if 'tag-list' in mbArtist:
                    for tag in mbArtist['tag-list']:
                        if tag:
                            t = string.capwords(tag['name'][:-1])
                            if not t in artistSearchResult.tags:
                                artistSearchResult.tags.append(t)
                artistSearchResult.alternateNames = []
                if 'alias-list' in mbArtist:
                    for a in mbArtist['alias-list']:
                        if a and 'alias' in a:
                            an = string.capwords(a['alias'][:-1])
                            if not an in artistSearchResult.alternateNames:
                                artistSearchResult.alternateNames.append(an)
            print(artistSearchResult)
            return artistSearchResult
        except:
            pass
        return None


    def __iTunesArtist(self, name):
        try:
            artistSearchResult = None
            url = "http://itunes.apple.com/search?term=" + parse.quote_plus(name) + "&entity=musicArtist"
            rq = request.Request(url=url)
            rq.add_header('Referer', self.referer)
            self.logger.debug("artistSearcher :: Performing iTunes Lookup For Artist")
            with request.urlopen(rq) as f:
                try:
                    s = StringIO((f.read().decode('utf-8')))
                    o = json.load(s)
                    for r in o['results']:
                        artistSearchResult = ArtistSearchResult(r['artistName'])
                        artistSearchResult.iTunesId = r['artistId']
                        artistSearchResult.amgId = r['amgArtistId']
                        if artistSearchResult.name.lower() == name.lower():
                            return artistSearchResult
                except:
                    pass
            return artistSearchResult
        except:
            pass
        return None


    def searchForArtistReleases(self,artistSearchResult, titleFilter=None):
        albumsSearchResult = self.__getAlbumsForArtistFromDB(artistSearchResult)
        if not albumsSearchResult:
            albumsSearchResult = self.__iTunesAlbumsForArtist(artistSearchResult, titleFilter)
            if albumsSearchResult:
                self.__saveReleasesForArtistToDB(artistSearchResult, albumsSearchResult)
        if titleFilter:
            for a in albumsSearchResult:
                if a.Title.lower() == titleFilter.lower():
                    albumsSearchResult = []
                    albumsSearchResult.append(a)
                    continue
        return albumsSearchResult


    def __iTunesAlbumsForArtist(self, artistSearchResult, titleFilter=None):
        url = "https://itunes.apple.com/lookup?id=" + str(artistSearchResult.iTunesId) + "&entity=album"
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
                            a = ArtistReleaseSearchResult(r['collectionName'], r['releaseDate'], r['trackCount'], r['artworkUrl100'])
                            a.iTunesId = r['collectionId']
                            albumsSearchResult.append(a)
                    except:
                        pass
            except:
                pass
        albumsSearchResult = sorted(albumsSearchResult, key=lambda x: x.releaseDate)
        return albumsSearchResult
