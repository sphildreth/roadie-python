import json
from io import StringIO
from urllib import request, parse
import musicbrainzngs
from searchEngines.searchEngineBase import SearchEngineBase
from searchEngines.searchResult import *


class MusicBrainz(SearchEngineBase):

    IsActive = True

    def __init__(self, referer=None):
        self.artists = {}
        self.searchReleases = {}
        self.releases = {}
        SearchEngineBase.__init__(self, referer)
        musicbrainzngs.set_useragent("Roadie", "0.1", self.referer)


    def lookupArtist(self, name):
        results = musicbrainzngs.search_artists(artist=name)
        if results and results['artist-list'][0]:
            result = results['artist-list'][0]
            if result:
                return self.lookupArtistByMusicBrainzId(result['id'])
        return None


    def lookupArtistByMusicBrainzId(self,musicbrainzId):
        if not musicbrainzId:
            raise RuntimeError("Invalid MusicBrainzId")
        try:
            artistSearchResult = None
            self.logger.debug("artistSearcher :: Performing MusicBrainz Lookup For Artist")
            results = musicbrainzngs.get_artist_by_id(musicbrainzId, includes=['tags','aliases','url-rels'])
            if results and results['artist']:
                result = results['artist']
                if result:
                    artistSearchResult = ArtistSearchResult(result['name'])
                    artistSearchResult.musicBrainzId = result['id']
                    artistSearchResult.artistType = result['type']
                    artistSearchResult.sortName = result['sort-name']
                    if 'isni-list' in result:
                        artistSearchResult.isniList = []
                        for isni in result['isni-list']:
                            if not isni in artistSearchResult.isniList:
                                artistSearchResult.isniList.append(isni)
                    if 'life-span' in result:
                        if 'begin' in result['life-span']:
                            artistSearchResult.beginDate = result['life-span']['begin']
                        if 'end' in result['life-span']:
                            artistSearchResult.endDate = result['life-span']['end']
                    if 'alias-list' in result:
                        artistSearchResult.alternateNames = []
                        for alias in result['alias-list']:
                            aliasName = alias['alias']
                            if aliasName not in artistSearchResult.alternateNames:
                                artistSearchResult.alternateNames.append(aliasName)
                    if 'url-relation-list' in result:
                        artistSearchResult.urls = []
                        for url in result['url-relation-list']:
                            target = url['target']
                            type = url['type']
                            if type != "image":
                                if not target in artistSearchResult.urls:
                                    artistSearchResult.urls.append(target)
                    if 'tag-list' in  result:
                        artistSearchResult.tags = []
                        for tag in result['tag-list']:
                            if tag not in artistSearchResult.tags:
                                artistSearchResult.tags.append(tag['name'])
            return artistSearchResult
        except:
            self.logger.exception("MusicBrainz: Error In LookupArtist")
            pass
        return None


    def searchForRelease(self, artistSearchResult, title):
        try:
            if not artistSearchResult.musicBrainzId:
                artistSearchResult = self.lookupArtist(artistSearchResult.name)
                if not artistSearchResult.musicBrainzId:
                    raise RuntimeError("Invalid ArtistSearchResult, MusicBrainzId Not Set")
            result = musicbrainzngs.search_releases(limit=1, arid=artistSearchResult.musicBrainzId, release=title,format='CD', country='US')
            if result and 'release-list' in result:
                mbReleaseId = result['release-list'][0]['id']
                return self.lookupReleaseByMusicBrainzId(mbReleaseId)
            return None
        except:
            pass


    def lookupReleaseByMusicBrainzId(self, musicbrainzId):
        try:
            if not musicbrainzId:
                raise RuntimeError("Invalid MusicBrainzId")
            albumSearchResult = None
            self.logger.debug("artistSearcher :: Performing MusicBrainz Lookup For Album(s)")
            mbReleaseById = musicbrainzngs.get_release_by_id(id=musicbrainzId, includes=['labels', 'aliases', 'recordings', 'url-rels'])
            if mbReleaseById:
                tracks = dict()
                labels = []
                coverUrl = self._getCoverArtUrl(musicbrainzId)
                if 'release' in mbReleaseById:
                    mbRelease = mbReleaseById['release']
                    if 'label-info-list' in mbRelease:
                        for labelInfo in mbRelease['label-info-list']:
                            label = ArtistReleaseLabelSearchResult(labelInfo['label']['name'])
                            label.musicBrainzId = labelInfo['label']['id']
                            label.sortName = labelInfo['label']['sort-name']
                            if 'alias-list' in labelInfo['label']:
                                label.alternateNames = []
                                for alias in labelInfo['label']['alias-list']:
                                    if not alias['alias'] in label.alternateNames:
                                        label.alternateNames.append(alias['alias'])
                            labels.append(label)
                    if 'medium-list' in mbRelease:
                        for medium in mbRelease['medium-list']:
                            releaseMediaNumber = medium['position']
                            if 'track-list' in medium:
                                for mbTrack in medium['track-list']:
                                    track = ArtistReleaseTrackSearchResult(mbTrack['recording']['title'])
                                    track.duration = mbTrack['length']
                                    track.trackNumber = mbTrack['position']
                                    track.releaseMediaNumber = releaseMediaNumber
                                    track.musicBrainzId = mbTrack['id']
                                    if not track.trackNumber in tracks:
                                        tracks[track.trackNumber] = track
                albumSearchResult = ArtistReleaseSearchResult(mbRelease['title'],mbRelease['date'], len(tracks),coverUrl)
                albumSearchResult.musicBrainzId = mbRelease['id']
                albumSearchResult.tracks = tracks
                albumSearchResult.labels = labels
            return albumSearchResult
        except:
            self.logger.exception("iTunes: Error In SearchForRelease")
            pass
        return None


    def _getCoverArtUrl(self,musicBrainzId):
        try:
            url = "http://coverartarchive.org/release/" + musicBrainzId + "/"
            rq = request.Request(url=url)
            rq.add_header('Referer', self.referer)
            self.logger.debug("artistSearcher :: Performing MusicBrainz Cover Art Lookup")
            with request.urlopen(rq) as f:
                try:
                    s = StringIO((f.read().decode('utf-8')))
                    o = json.load(s)
                    r = o['images']
                    if r:
                        for image in r:
                            if image['front'] == "true":
                                return image['image']
                except:
                    pass
        except:
            pass


# a = MusicBrainz()
# artist = a.lookupArtist('Billy Joel')
# release = a.searchForRelease(artist, "Cold Spring Harbor")
# #r = a.lookupReleaseByMusicBrainzId('76df3287-6cda-33eb-8e9a-044b5e15ffdd')
# print(artist)
# print(release)

