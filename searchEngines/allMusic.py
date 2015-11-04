import time
import hashlib
import json
from urllib.error import HTTPError
from io import StringIO
from urllib import request, parse

import arrow

from resources.common import *
from searchEngines.searchEngineBase import SearchEngineBase
from searchEngines.models.Artist import Artist, ArtistType
from searchEngines.models.Image import Image
from searchEngines.models.Genre import Genre
from searchEngines.models.Label import Label
from searchEngines.models.Release import Release
from searchEngines.models.ReleaseLabel import ReleaseLabel
from searchEngines.models.ReleaseMedia import ReleaseMedia
from searchEngines.models.Track import Track


class AllMusicGuide(SearchEngineBase):
    """
    AllMusicGuide search is very verbose in its albums for an Artist. Instead of just supplying the studio albums
        it returns all albums the Artist has appeared on.
    """
    IsActive = True

    cache = dict()

    api_url = 'http://api.rovicorp.com/data/v2'

    API_KEY = '5um457xsnur2a6hp43vuarrs'
    API_SECRET = 'SuGNstff77'

    def __init__(self, referer=None):
        SearchEngineBase.__init__(self, referer)

    def _sig(self):
        timestamp = int(time.time())
        m = hashlib.md5()
        m.update(self.API_KEY.encode('utf-8'))
        m.update(self.API_SECRET.encode('utf-8'))
        m.update(str(timestamp).encode('utf-8'))
        return m.hexdigest()

    def lookupArtist(self, name, fetchReleases=False):
        # http://api.rovicorp.com/search/v2.1/music/search?apikey=5um457xsnur2a6hp43vuarrs&sig=972d1b7669c7362c4789016442c03b93&query=Men+At+Work&entitytype=artist&include=all
        try:
            if name not in self.cache:
                artist = []
                include = "all"
                if not fetchReleases:
                    include = "images,aliases,associatedwith,groupmembers,musicstyles"
                url = "http://api.rovicorp.com/search/v2.1/music/search?apikey=" + self.API_KEY + "&sig=" + str(
                    self._sig()) + "&query=" + parse.quote_plus(
                    name) + "&entitytype=artist&include=" + include + "&size=1"
                rq = request.Request(url=url)
                rq.add_header('Referer', self.referer)
                self.logger.debug("Performing All Music Guide Lookup For Artist")
                with request.urlopen(rq) as f:
                    try:
                        s = StringIO((f.read().decode('utf-8')))
                        o = json.load(s)
                        if o:
                            if not 'searchResponse' in o or not 'results' in o['searchResponse']:
                                return None
                            amgArtist = o['searchResponse']['results'][0]['name']
                            if amgArtist:
                                artist = Artist(name=amgArtist['name'])
                                artist.amgId = amgArtist['ids']['nameId']
                                artist.artistType = ArtistType.Group if amgArtist['isGroup'] else ArtistType.Person
                                if 'musicGenres' in amgArtist and amgArtist['musicGenres']:
                                    if 'genre' in amgArtist['musicGenres']:
                                        artist.genres = []
                                        for genre in amgArtist['musicGenres']:
                                            if not isInList(artist.genres, genre):
                                                artist.genres.append(genre)
                                bd = None
                                if 'birth' in amgArtist and 'date' in amgArtist['birth']:
                                    bd = amgArtist['birth']['date'].replace("-??", "")
                                if bd:
                                    if artist.artistType == ArtistType.Person:
                                        artist.birthDate = parseDate(bd)
                                    else:
                                        artist.beginDate = parseDate(bd)
                                ed = (amgArtist['death']['date'] or '').replace("-??", "")
                                if ed:
                                    artist.endDate = parseDate(ed)
                                if 'discography' in amgArtist and amgArtist['discography']:
                                    artist.releases = []
                                    for album in amgArtist['discography']:
                                        release = Release(title=album['title'])
                                        release.amgId = album['ids']['albumId']
                                        rd = (album['year'] or '').replace("-??", "")
                                        if rd:
                                            release.releaseDate = parseDate(rd)
                                        release.releaseType = album['type']
                                        release.tags = []
                                        if 'flags' in album and album['flags']:
                                            for flag in album['flags']:
                                                if flag not in release.tags:
                                                    release.tags.append(flag)
                                        release.releaseLabels = []
                                        if album['label']:
                                            label = Label(name=album['label'], sortName=album['label'])
                                            release.releaseLabels.append(ReleaseLabel(label=label, release=release))
                                        release.releaseType = album['type']
                                        release.trackCount = 0
                                        artist.releases.append(release)
                                # TODO groupMembers
                                if 'images' in amgArtist:
                                    artist.images = []
                                    try:
                                        for image in amgArtist['images']:
                                            if image['formatid'] == 16:  # the largest images
                                                imageUrl = image['url']
                                                if imageUrl not in artist.images:
                                                    artist.images.append(Image(url=imageUrl))
                                    except:
                                        pass
                                try:
                                    if 'musicBioOverview' in amgArtist['musicBio']:
                                        artist.bioContext = amgArtist['musicBio']['musicBioOverview'][0]['overview']
                                except:
                                    pass
                                if 'musicStyles' in amgArtist and amgArtist['musicStyles']:
                                    artist.genres = []
                                    for style in amgArtist['musicStyles']:
                                        genreName = style['name']
                                        if not ([g for g in artist.genres if isEqual(g.name, genreName)]):
                                            artist.genres.append(Genre(name=genreName))
                                            # TODO associateWith
                    except HTTPError:
                        print("Spotify: Http Error")
                    except:
                        self.logger.exception("AllMusicGuide: Error In lookupArtist")
                        pass
                        # if artist:
                        #     print(artist.info())
                self.cache[name.lower()] = artist
            return self.cache[name.lower()]
        except:
            self.logger.exception("AllMusicGuide: Error In lookupArtist")
            pass
        return None

    def lookupReleaseDetails(self, amgId):
        try:
            release = None
            url = "http://api.rovicorp.com/data/v1.1/album/info?apikey=" + self.API_KEY + "&sig=" + str(
                self._sig()) + "&include=images,releases,styles,tracks&albumid=" + amgId
            rq = request.Request(url=url)
            rq.add_header('Referer', self.referer)
            self.logger.debug("Performing All Music Guide Lookup For Release(s)")
            with request.urlopen(rq) as f:
                try:
                    s = StringIO((f.read().decode('utf-8')))
                    o = json.load(s)
                    if o:
                        if 'status' in o and o['status'] == "ok":
                            album = o['album']
                            if album:
                                release = Release(title=album['title'])
                                release.amgId = amgId
                                release.tags = []
                                if 'flags' in album and album['flags']:
                                    for flag in album['flags']:
                                        if not isInList(release.tags, flag):
                                            release.tags.append(flag)
                                rd = (album['originalReleaseDate'] or '').replace("-??", "")
                                if rd:
                                    release.releaseDate = parseDate(rd)
                                if 'genres' in album and album['genres']:
                                    release.genres = []
                                    for style in album['genres']:
                                        genreName = style['name']
                                        if not ([g for g in release.genres if isEqual(g.name, genreName)]):
                                            release.genres.append(Genre(name=genreName))
                                if 'styles' in album and album['styles']:
                                    release.genres = release.genres or []
                                    for style in album['styles']:
                                        genreName = style['name']
                                        if not ([g for g in release.genres if isEqual(g.name, genreName)]):
                                            release.genres.append(Genre(name=genreName))
                                if 'tracks' in album and album['tracks']:
                                    trackCount = 0
                                    currentTrack = 0
                                    releaseMedia = []
                                    for disc in set(map(lambda x: x['disc'], album['tracks'])):
                                        media = ReleaseMedia(releaseMediaNumber=disc)
                                        media.tracks = []
                                        for amgTrack in (
                                                [t for t in album['tracks'] if isEqual(str(t['disc']), str(disc))]):
                                            currentTrack += 1
                                            track = Track(title=amgTrack['title'])
                                            track.duration = amgTrack['duration']
                                            track.trackNumber = currentTrack
                                            track.releaseMediaNumber = disc
                                            track.amgId = amgTrack['ids']['trackId']
                                            if not [t for t in media.tracks if isEqual(t.title, amgTrack['title'])]:
                                                media.tracks.append(track)
                                        trackCount += len(media.tracks)
                                        releaseMedia.append(media)
                                    release.media = releaseMedia
                                    release.mediaCount = len(releaseMedia)
                                if not release.alternateNames:
                                    release.alternateNames = []
                                cleanedTitle = createCleanedName(release.title)
                                if cleanedTitle not in release.alternateNames and cleanedTitle != release.title:
                                    release.alternateNames.append(cleanedTitle)
                except:
                    self.logger.exception("AllMusicGuide: Error In lookupArtist")
                    pass
            return release
        except:
            self.logger.exception("AllMusicGuide: Error In lookupArtist")
            pass
        return None

    def searchForRelease(self, artist, title):
        if not artist.name.lower() in self.cache:
            amgArtist = self.lookupArtist(artist.name)
        else:
            amgArtist = self.cache[artist.name.lower()]
        releases = []
        if amgArtist and amgArtist.releases and title:
            release = [r for r in amgArtist.releases if isEqual(r.title, title)]
            if release:
                releases.append(self.lookupReleaseDetails(release[0].amgId))
        else:
            for release in amgArtist.releases:
                r = self.lookupReleaseDetails(release.amgId)
                if r:
                    releases.append(r)
        return releases

# a = AllMusicGuide()
# artist = a.lookupArtist('Men At Work')
# #release = a.lookupReleaseDetails(artist.releases[0].amgId)
# #release = a.lookupReleaseDetails("MW0000190875")
# releast = a.searchForRelease(artist, "Cargo")
# print(artist)
