import os
import sqlite3
import json
import string
from io import StringIO
from urllib import request, parse
from resources.logger import Logger
from resources.musicBrainz import MusicBrainz
from mongoengine import connect
from resources.models import Artist, Release, Track, TrackRelease

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
        self.roadieId = None

    def __str__(self):
        return "Id [" + str(self.id) + "], RoadieId [" + str(self.roadieId) + "], MusicBrainzId [" + str(self.musicBrainzId) + "], " + \
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
        self.roadieId = None

    def __str__(self):
       return "Id [" + str(self.id) + ", RoadieId [" + str(self.roadieId) + "], MusicBrainzId [" + str(self.musicBrainzId) + "], ITunesId [" + str(self.iTunesId) + \
              "], ReleaseDate [" + str(self.releaseDate) + "], TrackCount [" + str(self.trackCount) + "], Title [" + str(self.title) + "]"


class ArtistSearcher(object):

    databaseFilename = "artistsReference.db"

    def __init__(self, referer=None):
        self.referer = referer
        if not self.referer or self.referer.startswith("http://localhost"):
            self.referer = "http://github.com/sphildreth/roadie"
        self.logger = Logger()
        d = os.path.dirname(os.path.realpath(__file__)).split(os.sep)
        path = os.path.join(os.sep.join(d[:-1]), "settings.json")
        with open(path, "r") as rf:
            config = json.load(rf)
        self.dbName = config['MONGODB_SETTINGS']['DB']
        self.host = config['MONGODB_SETTINGS']['host']
        self.mongoClient = connect(self.dbName, host=self.host)

    def __enter__(self):
        self.conn = sqlite3.connect(self.databaseFilename)
        c = self.conn.cursor()
        c.execute("create table if not exists Artists (id INTEGER PRIMARY KEY, roadieId text, musicBrainzId text, iTunesId integer, amgId integer, beginDate text, endDate text, artistType text, imageUrl text, name text, sortName text)")
        c.execute("create index if not exists ArtistName on Artists (name)")
        c.execute("create table if not exists ArtistTags (id INTEGER PRIMARY KEY, artistId integer, tag text)")
        c.execute("create index if not exists ArtistTagsArtistId on ArtistTags (artistId)")
        c.execute("create table if not exists ArtistAlternateNames (id INTEGER PRIMARY KEY, artistId integer, name text)")
        c.execute("create index if not exists ArtistAlternateNamesArtistId on ArtistAlternateNames (artistId)")
        c.execute("create table if not exists Releases (id INTEGER PRIMARY KEY, artistId integer, roadieId text, musicBrainzId text, iTunesId integer, title text, releaseDate text, trackCount integer, coverUrl text)")
        c.execute("create index if not exists ReleasesArtistId on Releases (artistId)")
        self.conn.commit()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()
        self.mongoClient.close()

    def __getArtistFromDB(self,name):
        c = self.conn.cursor()
        sql = 'SELECT * FROM Artists WHERE name = "' + name + '" COLLATE NOCASE'
        c.execute(sql)
        r = c.fetchone()
        if r:
            re = ArtistSearchResult(r[9])
            re.id = r[0]
            re.roadieId = r[1]
            re.musicBrainzId = r[2]
            re.iTunesId = r[3]
            re.amgId = r[4]
            re.sortName = r[10]
            re.beginDate = r[5]
            re.endDate = r[6]
            re.artistType = r[7]
            re.imageUrl = r[8]
            sql = 'SELECT * FROM ArtistTags WHERE artistId = ' + str(re.id)
            c.execute(sql)
            rs = c.fetchall()
            re.tags = []
            for r in rs:
                re.tags.append(r[2])
            sql = 'SELECT * FROM ArtistAlternateNames WHERE artistId = ' + str(re.id)
            c.execute(sql)
            rs = c.fetchall()
            re.alternateNames = []
            for r in rs:
                re.alternateNames.append(r[2])
            return re
        else:
            return None

    def __saveArtistToDB(self,artistSearchResult):
        c = self.conn.cursor()
        mbId = "null"
        if artistSearchResult.musicBrainzId:
            mbId = '"' + artistSearchResult.musicBrainzId + '"'
        sql = 'INSERT INTO Artists (roadieId, musicBrainzId, iTunesId, amgId, beginDate, endDate, artistType, imageUrl, name, sortName) VALUES ("' + \
              str(artistSearchResult.roadieId) + '",' + \
              mbId + ',' + \
              str(artistSearchResult.iTunesId) + ',' + \
              str(artistSearchResult.amgId or 0) + ',"' + \
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
                    sql = 'INSERT INTO ArtistTags (artistId, tag) VALUES (' + str(artistSearchResult.id) + ',"' + str(tag) + '")'
                    c.execute(sql)
        self.conn.commit()

    def __saveArtistAlternateNamesToDB(self,artistSearchResult):
        c = self.conn.cursor()
        if artistSearchResult.alternateNames:
            for alternateName in artistSearchResult.alternateNames:
                if alternateName:
                    sql = 'INSERT INTO ArtistAlternateNames (artistId, name) VALUES (' + str(artistSearchResult.id) + ',"' + str(alternateName) + '")'
                    c.execute(sql)
        self.conn.commit()


    def __getAlbumsForArtistFromDB(self,artistSearchResult):
        c = self.conn.cursor()
        sql = 'SELECT * FROM Releases WHERE artistId = ' + str(artistSearchResult.id)
        c.execute(sql)
        rs = c.fetchall()
        releases = []
        for r in rs:
            release = ArtistReleaseSearchResult(r[5], r[6], r[7], r[8])
            release.id = r[0]
            release.roadieId = r[2]
            release.musicBrainzId = r[3]
            release.iTunesId = r[4]
            releases.append(release)
        return releases

    def __markArtistFoundInRoadie(self,artistSearchResult):
        artist = Artist.objects(__raw__= {'$or' : [
            { 'Name' : { '$regex' : artistSearchResult.name, '$options': 'mi' }},
            { 'SortName': { '$regex' : artistSearchResult.name, '$options': 'mi' } },
            { 'AlternateNames': { '$regex' : artistSearchResult.name, '$options': 'mi' } }
        ]}).first()
        if artist:
            artistSearchResult.roadieId = artist.id
        return artistSearchResult

    def __markReleasesFoundInRoadie(self, artistSearchResult, artistReleaseSearchResults):
        if artistSearchResult.roadieId:
            artist = Artist.objects(id=artistSearchResult.roadieId).first()
            for r in artistReleaseSearchResults:
                release = Release.objects(__raw__= {'$or' : [
                        { 'Title' : { '$regex' : r.title, '$options': 'mi' }},
                        { 'AlternateNames': { '$regex' : r.title, '$options': 'mi' } }
                    ]}).filter(Artist = artist).first()
                if release:
                    r.roadieId = release.id
        return artistReleaseSearchResults

    def __saveReleasesForArtistToDB(self,artistSearchResult, ArtistReleaseSearchResults):
        c = self.conn.cursor()
        for artistReleaseSearchResult in ArtistReleaseSearchResults:
            sql = 'INSERT INTO Releases (artistId, roadieId, musicBrainzId, iTunesId, title, releaseDate, trackCount, coverUrl) VALUES (' + \
                  str(artistSearchResult.id) + ',"' + \
                  str(artistReleaseSearchResult.roadieId) + '","' +  \
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
                artistSearchResult.name = mbArtist.name
                artistSearchResult.sortName = mbArtist.sortName
                artistSearchResult.beginDate = mbArtist.beginDate
                artistSearchResult.endDate = mbArtist.endDate
                artistSearchResult.artistType = mbArtist.artistType
            itArtist = self.__iTunesArtist(name)
            if itArtist:
                if itArtist.name and itArtist.name.lower() != "none":
                    artistSearchResult.name = itArtist.name
                artistSearchResult.iTunesId = itArtist.iTunesId
                artistSearchResult.amgId = itArtist.amgId
            if artistSearchResult:
                artistSearchResult = self.__markArtistFoundInRoadie(artistSearchResult)
            self.__saveArtistToDB(artistSearchResult)
            artistSearchResult = self.__getArtistFromDB(name)
            if mbArtist:
                artistSearchResult.tags = mbArtist.tags
                artistSearchResult.alternateNames = mbArtist.alternateNames
                self.__saveArtistTagsToDB(artistSearchResult)
                self.__saveArtistAlternateNamesToDB(artistSearchResult)
            artistSearchResult = self.__getArtistFromDB(name)
        foundArtistName = None
        if artistSearchResult:
            foundArtistName = artistSearchResult.name
        self.logger.debug("artistSearcher :: searchForArtist Name [" + name + "] Found [" + str(foundArtistName) + "]")
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
                            t = string.capwords(tag['name'])
                            if not t in artistSearchResult.tags:
                                artistSearchResult.tags.append(t)
                artistSearchResult.alternateNames = []
                if 'alias-list' in mbArtist:
                    for a in mbArtist['alias-list']:
                        if a and 'alias' in a:
                            an = string.capwords(a['alias'])
                            if not an in artistSearchResult.alternateNames:
                                artistSearchResult.alternateNames.append(an)
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
                albumsSearchResult = self.__markReleasesFoundInRoadie(artistSearchResult, albumsSearchResult)
                self.__saveReleasesForArtistToDB(artistSearchResult, albumsSearchResult)
        result = albumsSearchResult
        if titleFilter:
            result = []
            for a in albumsSearchResult:
                if a.title.lower() == titleFilter.lower():
                    result.append(a)
                    continue
        return result


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
