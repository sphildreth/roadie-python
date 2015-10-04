import json
from io import StringIO
from urllib import request, parse

from searchEngines.searchEngineBase import SearchEngineBase
from resources.models.Artist import Artist
from resources.models.Release import Release
from resources.models.ReleaseMedia import ReleaseMedia
from resources.models.Track import Track


class Spotify(SearchEngineBase):

    IsActive = True

    def __init__(self, referer = None):
        SearchEngineBase.__init__(self, referer)

    def lookupArtist(self, name):
        try:
            artist = None
            url = "https://api.spotify.com/v1/search?offset=0&limit=1&type=artist&query=" + parse.quote_plus(name)
            rq = request.Request(url=url)
            rq.add_header('Referer', self.referer)
            self.logger.debug("artistSearcher :: Performing Spotify Lookup For Artist")
            with request.urlopen(rq) as f:
                try:
                    s = StringIO((f.read().decode('utf-8')))
                    o = json.load(s)
                    ar = o['artists']
                    if ar and 'items' in ar:
                        r = ar['items'][0]
                        artist = Artist(name=r['name'])
                        artist.spotifyId = r['id']
                        artist.artistType = r['type']
                        if 'external_urls' in r and 'spotify' in r['external_urls']:
                            artist.urls = []
                            artist.urls.append(r['external_urls']['spotify'])
                        if 'genres' in r:
                            artist.tags = artist.tags or []
                            for genre in r['genres']:
                                if genre not in artist.tags:
                                    artist.tags.append(genre)
                        images = r['images']
                        if images:
                            artist.imageUrl = images[0]['url']
                except:
                    self.logger.exception("LastFM: Error In LookupArtist")
                    pass
                    #    if artist:
                    #         print(artist.info())
            return artist
        except:
            pass
        return None


    def searchForRelease(self, artistSearchResult, title):
        try:
            url = "https://api.spotify.com/v1/artists/" + str(artistSearchResult.spotifyId) + "/albums?offset=0&limit=20&album_type=album"
            rq = request.Request(url=url)
            rq.add_header('Referer', self.referer)
            with request.urlopen(rq) as f:
                s = StringIO((f.read().decode('utf-8')))
                o = json.load(s)
                spotifyReleases = o['items']
                if spotifyReleases:
                    for spotifyRelease in spotifyReleases:
                        spotifyReleaseName = spotifyRelease['name']
                        if spotifyReleaseName.lower().strip() == title.lower().strip():
                            return self.lookupReleaseBySpotifyId(spotifyRelease['id'])
            return None
        except:
            pass
        return None


    def lookupReleaseBySpotifyId(self, spotifyId):
        try:
            release = None
            url = "https://api.spotify.com/v1/albums/" + spotifyId
            rq = request.Request(url=url)
            rq.add_header('Referer', self.referer)
            self.logger.debug("artistSearcher :: Performing Spotify Lookup For Release")
            with request.urlopen(rq) as f:
                try:
                    s = StringIO((f.read().decode('utf-8')))
                    o = json.load(s)
                    if o:
                        media = ReleaseMedia(releaseMediaNumber=1)
                        media.tracks = []
                        tags = []
                        urls = []
                        if 'tracks' in o and 'items' in o['tracks']:
                            for spTrack in o['tracks']['items']:
                                track = Track(title=spTrack['name'])
                                track.trackNumber = spTrack['track_number']
                                track.dur = spTrack['duration_ms']
                                track.releaseMediaNumber = spTrack['disc_number']
                                track.spotifyId = spTrack['id']
                                if not filter(lambda x: x.trackNumber == track.trackNumber, media.tracks):
                                    media.tracks.append(track)
                        if 'genres' in o:
                            for genre in o['genres']:
                                if genre not in tags:
                                    tags.append(genre)
                        if 'external_ids' in o and 'upc' in o['external_ids']:
                            tags.append("upc:" + o['external_ids']['upc'])
                        if 'external_urls' in o and 'spotify' in o['external_urls']:
                            urls.append(o['external_urls']['spotify'])
                        coverUrl = None
                        images = o['images']
                        if images:
                            coverUrl = images[0]['url']
                        release = Release(title=o['name'], releaseDate=o['release_date'], trackCount=len(media.tracks),
                                          coverUrl=coverUrl)
                        release.spotifyId = o['id']
                        release.tags = tags
                        release.urls = urls
                    return release
                except:
                    pass
                return release
        except:
            pass
        return None


# a = Spotify()
# artist = a.lookupArtist('Men At Work')
# release = a.searchForRelease(artist, "Cargo")
# #r = a.lookupReleaseByMusicBrainzId('76df3287-6cda-33eb-8e9a-044b5e15ffdd')
# print(artist)
# print(release)
