import os

import json
import string
from io import StringIO
from urllib import request, parse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mongoengine import connect

from resources.logger import Logger

from searchEngines.musicBrainz import MusicBrainz
from searchEngines.iTunes import iTunes
from searchEngines.allMusic import AllMusicGuide
from searchEngines.lastFM import LastFM
from searchEngines.spotify import Spotify

from resources.models import Artist, Release
from searchEngines.searchResult import *

Base = declarative_base()


class ArtistSearcher(object):

    databaseFilename = "sqlite:///artistsSearchReference.db"
    dbSession = None

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
        engine = create_engine(self.databaseFilename)
        Base.metadata.bind = engine
        DBSession = sessionmaker(bind=engine)
        self.dbSession = DBSession()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __getArtistFromDB(self,name):
        return self.dbSession.query(ArtistSearchResult).filter(ArtistSearchResult.name == name).first()


    def __saveArtistToDB(self,artistSearchResult):
        self.dbSession.add(artistSearchResult)
        self.dbSession.commit()

    def __saveArtistTagsToDB(self,artistSearchResult):
        # c = self.conn.cursor()
        # if artistSearchResult.tags:
        #     for tag in artistSearchResult.tags:
        #         if tag:
        #             sql = 'INSERT INTO ArtistTags (artistId, tag) VALUES (' + str(artistSearchResult.id) + ',"' + str(tag) + '")'
        #             c.execute(sql)
        # self.conn.commit()
        pass

    def __saveArtistAlternateNamesToDB(self,artistSearchResult):
        # c = self.conn.cursor()
        # if artistSearchResult.alternateNames:
        #     for alternateName in artistSearchResult.alternateNames:
        #         if alternateName:
        #             sql = 'INSERT INTO ArtistAlternateNames (artistId, name) VALUES (' + str(artistSearchResult.id) + ',"' + str(alternateName) + '")'
        #             c.execute(sql)
        # self.conn.commit()
        pass


    def __getAlbumsForArtistFromDB(self,artistSearchResult):
        # c = self.conn.cursor()
        # sql = 'SELECT * FROM Releases WHERE artistId = ' + str(artistSearchResult.id)
        # c.execute(sql)
        # rs = c.fetchall()
        # releases = []
        # for r in rs:
        #     release = ArtistReleaseSearchResult(r[5], r[6], r[7], r[8])
        #     release.id = r[0]
        #     release.roadieId = r[2]
        #     release.musicBrainzId = r[3]
        #     release.iTunesId = r[4]
        #     releases.append(release)
        # return releases
        pass

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
        # c = self.conn.cursor()
        # for artistReleaseSearchResult in ArtistReleaseSearchResults:
        #     sql = 'INSERT INTO Releases (artistId, roadieId, musicBrainzId, iTunesId, title, releaseDate, trackCount, coverUrl) VALUES (' + \
        #           str(artistSearchResult.id) + ',"' + \
        #           str(artistReleaseSearchResult.roadieId) + '","' +  \
        #           str(artistReleaseSearchResult.musicBrainzId) + '",' +  \
        #           str(artistReleaseSearchResult.iTunesId) + ',"' +  \
        #           str(artistReleaseSearchResult.title) + '","' + \
        #           str(artistReleaseSearchResult.releaseDate) + '",' + \
        #           str(artistReleaseSearchResult.trackCount)  + ',"' + \
        #           str(artistReleaseSearchResult.coverUrl) + '")'
        #     c.execute(sql)
        # self.conn.commit()
        pass

    def searchForArtist(self, name):
        artistSearchResult = self.__getArtistFromDB(name)
        if not artistSearchResult:
            artistSearchResult = ArtistSearchResult(name)

            iTunesSearcher = iTunes(self.referer)
            if iTunesSearcher.IsActive:
                artistSearchResult = self.__mergeArtistResult(artistSearchResult, iTunesSearcher.lookupArtist(name))
            mbSearcher = MusicBrainz(self.referer)
            if mbSearcher.IsActive:
                artistSearchResult = self.__mergeArtistResult(artistSearchResult, mbSearcher.lookupArtist(name))
            lastFMSearcher = LastFM(self.referer)
            if lastFMSearcher.IsActive:
                artistSearchResult = self.__mergeArtistResult(artistSearchResult, lastFMSearcher.lookupArtist(name))
            spotifySearcher = Spotify(self.referer)
            if spotifySearcher.IsActive:
                artistSearchResult = self.__mergeArtistResult(artistSearchResult, spotifySearcher.lookupArtist(name))
            allMusicSearcher = AllMusicGuide(self.referer)
            if allMusicSearcher.IsActive:
                artistSearchResult = self.__mergeArtistResult(artistSearchResult, allMusicSearcher.lookupArtist(name))
            if artistSearchResult:
                artistSearchResult = self.__markArtistFoundInRoadie(artistSearchResult)
                self.__saveArtistToDB(artistSearchResult)
            #    artistSearchResult = self.__getArtistFromDB(name)
        foundArtistName = None
        if artistSearchResult:
            foundArtistName = artistSearchResult.name
        self.logger.debug("artistSearcher :: searchForArtist Name [" + name + "] Found [" + str(foundArtistName) + "]")
        return artistSearchResult

    def __mergeArtistResult(self, left, right):
        result = left
        if not result.name and right.name:
            result.name = right.name
        elif right.name and result.name.lower().strip() != right.name.lower().strip():
            if not result.alternateNames:
                result.alternateNames = []
            if not right.name in result.alternateNames:
                result.alternateNames.append(right.name)
        result.sortName = result.sortName or right.sortName
        result.musicBrainzId = result.musicBrainzId or right.musicBrainzId
        result.iTunesId = result.iTunesId or right.iTunesId
        result.amgId = result.amgId or right.amgId
        result.spotifyId = result.spotifyId or right.spotifyId
        result.beginDate = result.beginDate or right.beginDate
        result.endDate = result.endDate or right.endDate
        if not result.artistType or result.artistType.lower().strip() == "unknown" and right.artistType:
            result.artistType = right.artistType
        result.imageUrl = result.imageUrl or right.imageUrl
        result.bioContext = result.bioContext or right.bioContext
        if not result.tags and right.tags:
            result.tags = right.tags
        elif result.tags and right.tags:
            for tag in right.tags:
                if not tag in result.tags:
                    result.tag.append(tag)
        if not result.alternateNames and right.alternateNames:
            result.alternateNames = right.alternateNames
        elif result.alternateNames and right.alternateNames:
            for alternateName in right.alternateNames:
                if not alternateName in result.alternateNames:
                    result.alternateNames.append(alternateName)
        if not result.urls and right.urls:
            result.urls = right.urls
        elif result.urls and right.urls:
            for url in right.urls:
                if not url in result.urls:
                    result.urls.append(url)
        if not result.isniList and right.isniList:
            result.isniList = right.isniList
        elif result.isniList and right.isniList:
            for isni in right.isniList:
                if not isni in result.isniList:
                    result.isniList.append(isni)
        if not result.releases and right.releases:
            result.releases = right.releases
        elif result.releases and right.releases:
            for release in right.releases:
                if not filter(lambda x: x.title == release.title, result.releases):
                    result.releases.append(release)
        return result

    def searchForArtistReleases(self,artistSearchResult, titleFilter=None):
        # albumsSearchResult = self.__getAlbumsForArtistFromDB(artistSearchResult)
        # if not albumsSearchResult:
        #     albumsSearchResult = self.__iTunesAlbumsForArtist(artistSearchResult, titleFilter)
        #     if albumsSearchResult:
        #         albumsSearchResult = self.__markReleasesFoundInRoadie(artistSearchResult, albumsSearchResult)
        #         self.__saveReleasesForArtistToDB(artistSearchResult, albumsSearchResult)
        # result = albumsSearchResult
        # if titleFilter:
        #     result = []
        #     for a in albumsSearchResult:
        #         if a.title.lower() == titleFilter.lower():
        #             result.append(a)
        #             continue
        # return result
        pass


with ArtistSearcher(None) as s:
    b = s.searchForArtist("Men At Work")
    print(b)


