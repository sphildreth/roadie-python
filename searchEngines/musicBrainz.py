import json
import threading
from queue import Queue
from io import StringIO
from urllib import request

import arrow
import musicbrainzngs

from resources.common import *
from searchEngines.searchEngineBase import SearchEngineBase, ThreadData
from searchEngines.models.Artist import Artist, ArtistType
from searchEngines.models.Label import Label
from searchEngines.models.Release import Release
from searchEngines.models.ReleaseLabel import ReleaseLabel
from searchEngines.models.ReleaseMedia import ReleaseMedia
from searchEngines.models.Track import Track


class MusicBrainz(SearchEngineBase):
    IsActive = True

    threadDataType = "musicBrainz"
    lock = threading.Lock()
    que = Queue()

    cache = dict()

    artistReleasesThreaded = []

    def __init__(self, referer=None):
        self.artists = {}
        self.searchReleases = {}
        self.releases = {}
        SearchEngineBase.__init__(self, referer)
        musicbrainzngs.set_useragent("Roadie", "0.1", self.referer)

    def lookupArtist(self, name):
        results = musicbrainzngs.search_artists(artist=name)
        if results and 'artist-list' in results and results['artist-list']:
            result = None
            for artistResult in results['artist-list']:
                if 'name' in artistResult:
                    if isEqual(artistResult['name'], name):
                        result = artistResult
                        break
            if result:
                return self.lookupArtistByMusicBrainzId(result['id'])
        return None

    def lookupArtistByMusicBrainzId(self, musicBrainzId, fetchReleases=False):
        if not musicBrainzId:
            raise RuntimeError("Invalid MusicBrainzId")
        try:
            artist = None
            self.logger.debug("Performing MusicBrainz Lookup For Artist")
            results = musicbrainzngs.get_artist_by_id(musicBrainzId, includes=['tags', 'aliases', 'url-rels'])
            if results and results['artist']:
                result = results['artist']
                if result:
                    artist = Artist(name=result['name'])
                    artist.musicBrainzId = result['id']
                    artist.artistType = ArtistType.Person
                    if 'type' in result and isEqual(result['type'], "group"):
                        artist.artistType = ArtistType.Group
                    artist.sortName = result['sort-name']
                    if 'isni-list' in result:
                        artist.isniList = []
                        for isni in result['isni-list']:
                            if not isInList(artist.isniList, isni):
                                artist.isniList.append(isni)
                    if 'life-span' in result:
                        if 'begin' in result['life-span']:
                            artist.beginDate = result['life-span']['begin']
                        if 'end' in result['life-span']:
                            artist.endDate = result['life-span']['end']
                    if 'alias-list' in result:
                        artist.alternateNames = []
                        for alias in result['alias-list']:
                            aliasName = alias['alias']
                            if not isInList(artist.alternateNames, aliasName):
                                artist.alternateNames.append(aliasName)
                    if 'url-relation-list' in result:
                        artist.urls = []
                        for url in result['url-relation-list']:
                            target = url['target']
                            imageType = url['type']
                            if imageType != "image":
                                if not isInList(artist.urls, target):
                                    artist.urls.append(target)
                    if 'tag-list' in result:
                        artist.tags = []
                        for tag in result['tag-list']:
                            if not isInList(artist.tags, tag['name']):
                                artist.tags.append(tag['name'])
            if artist and fetchReleases:
                artist.releases = self.lookupAllArtistsReleases(artist)
                #      print(artist.info())
            return artist
        except:
            self.logger.exception("MusicBrainz: Error In LookupArtist")
            pass
        return None

    def searchForRelease(self, artist, title):
        try:
            if artist.roadieId in self.cache and not title:
                self.logger.debug(
                    "Found Artist: roadieId [" + artist.roadieId + "] name [" + artist.name + "] in MusicBrainz Cache.")
                return self.cache[artist.roadieId]
            if not artist.musicBrainzId:
                artist = self.lookupArtist(artist.name)
                if not artist or not artist.musicBrainzId:
                    return None
            if artist.roadieId not in self.cache:
                self.cache[artist.roadieId] = self.lookupAllArtistsReleases(artist)
            else:
                self.logger.debug(
                    "Found Artist: roadieId [" + artist.roadieId + "] name [" + artist.name + "] in MusicBrainz Cache.")
            if title:
                foundRelease = None
                for release in self.cache[artist.roadieId]:
                    if isEqual(release.title, title):
                        foundRelease = release
                        break
                if foundRelease:
                    releases = [foundRelease]
                    return releases
                else:
                    return None
            return self.cache[artist.roadieId]
        except:
            self.logger.exception("MusicBrainz: Error In LookupArtist")
            pass

    def lookupAllArtistsReleases(self, artist):
        mbReleases = musicbrainzngs.browse_releases(artist=artist.musicBrainzId)
        if mbReleases and 'release-list' in mbReleases:

            for x in range(self.threadCount):
                t = threading.Thread(target=self.threader)
                t.daemon = True
                t.start()

            for mbRelease in mbReleases['release-list']:
                self.que.put(ThreadData(self.threadDataType, mbRelease['id']))

            self.que.join()

            return self.artistReleasesThreaded

        return None

    def threader(self):
        while True:
            threadData = self.que.get()
            if threadData.threadDataType == self.threadDataType:
                self.threaderLookupRelease(threadData.data)
                self.que.task_done()

    def threaderLookupRelease(self, releaseMusicBrainzId):
        release = self.lookupReleaseByMusicBrainzId(releaseMusicBrainzId)
        if release:
            with self.lock:
                if release in self.artistReleasesThreaded:
                    for r in self.artistReleasesThreaded:
                        if r == release:
                            r.mergeWithRelease(release)
                else:
                    self.artistReleasesThreaded.append(release)

    def lookupReleaseByMusicBrainzId(self, musicBrainzId):
        try:
            if not musicBrainzId:
                raise RuntimeError("Invalid MusicBrainzId")
            release = None
            self.logger.debug("Performing MusicBrainz Lookup For Album(s) [" + musicBrainzId + "]")
            mbReleaseById = musicbrainzngs.get_release_by_id(id=musicBrainzId,
                                                             includes=['labels', 'aliases', 'recordings', 'release-groups', 'media', 'url-rels'])
            if mbReleaseById:
                releaseLabels = []
                releaseMedia = []
                trackCount = 0
                coverUrl = self._getCoverArtUrl(musicBrainzId)
                if 'release' in mbReleaseById:
                    mbRelease = mbReleaseById['release']
                    releaseDate = None
                    releaseType = None
                    if 'release-group' in mbRelease and mbRelease['release-group']:
                        if 'first-release-date' in mbRelease['release-group'] and mbRelease['release-group']['first-release-date']:
                            releaseDate = parseDate(mbRelease['release-group']['first-release-date'])
                        if 'type' in mbRelease['release-group'] and mbRelease['release-group']['type']:
                            releaseType = mbRelease['release-group']['type']
                        if not releaseType and 'primary-type' in mbRelease['release-group'] and mbRelease['release-group']['primary-type']:
                            releaseType = mbRelease['release-group']['primary-type']
                    release = Release(title=mbRelease['title'], releaseDate=releaseDate)
                    release.releaseType = releaseType
                    if 'label-info-list' in mbRelease:
                        labelsFound = []
                        for labelInfo in mbRelease['label-info-list']:
                            if 'label' in labelInfo and 'name' in labelInfo['label']:
                                label = None
                                labelName = labelInfo['label']['name']
                                if labelName not in labelsFound:
                                    if labelName:
                                        label = Label(name=labelName)
                                        label.musicBrainzId = labelInfo['label']['id']
                                        labelSortName = labelInfo['label']['sort-name']
                                        label.sortName = labelSortName or labelName
                                    if 'alias-list' in labelInfo['label']:
                                        label.alternateNames = []
                                        for alias in labelInfo['label']['alias-list']:
                                            if not isInList(label.alternateNames, alias['alias']):
                                                label.alternateNames.append(alias['alias'])
                                    catalogNumber = None
                                    if 'catalog-number' in labelInfo:
                                        catalogNumber = labelInfo['catalog-number']
                                    releaseLabels.append(
                                        ReleaseLabel(catalogNumber=catalogNumber, label=label, release=release))
                                    labelsFound.append(labelName)
                    if 'medium-list' in mbRelease:
                        for medium in mbRelease['medium-list']:
                            releaseMediaNumber = medium['position']
                            media = ReleaseMedia(releaseMediaNumber=releaseMediaNumber)
                            media.tracks = []
                            if 'track-list' in medium and medium['track-list']:
                                for mbTrack in medium['track-list']:
                                    track = Track(title=mbTrack['recording']['title'])
                                    if 'length' in mbTrack:
                                        track.duration = mbTrack['length']
                                    track.trackNumber = mbTrack['position']
                                    track.releaseMediaNumber = releaseMediaNumber
                                    track.musicBrainzId = mbTrack['id']
                                    if not ([t for t in media.tracks if t.trackNumber == track.trackNumber]):
                                        media.tracks.append(track)
                            trackCount += len(media.tracks)
                            media.trackCount = len(media.tracks)
                            releaseMedia.append(media)
                release.trackCount = trackCount
                release.coverUrl = coverUrl
                release.musicBrainzId = musicBrainzId
                release.media = releaseMedia
                release.releaseLabels = releaseLabels
                if not release.alternateNames:
                    release.alternateNames = []
                cleanedTitle = createCleanedName(release.title)
                if cleanedTitle not in release.alternateNames and cleanedTitle != release.title:
                    release.alternateNames.append(cleanedTitle)
            return release
        except:
            self.logger.exception("MusicBrainy: Error In SearchForRelease")
            pass
        return None

    def _getCoverArtUrl(self, musicBrainzId):
        try:
            url = "http://coverartarchive.org/release/" + musicBrainzId + "/"
            rq = request.Request(url=url)
            rq.add_header('Referer', self.referer)
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
# artist = a.lookupArtist('Danger Danger')
# #uprint(artist.info())
#
# release = a.lookupReleaseByMusicBrainzId("ae694c34-dbf4-31a3-89fc-1f2328ed53f4")
# uprint(release.info())

#
# release = a.lookupReleaseByMusicBrainzId("2990c4bd-d04f-4319-93a5-d95515bfb493")
# print(release.info())
#
# #r = a.lookupAllArtistsReleases(artist)
# # #release = a.searchForRelease(artist, "Cold Spring Harbor")
# #r = a.lookupReleaseByMusicBrainzId('038acd9c-b845-461e-ae76-c4f3190fc774')
# #print(r)
# # #print(artist.info())
# #print(release.info())
