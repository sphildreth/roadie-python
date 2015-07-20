# MusicBrainz interface for Roadie

import musicbrainzngs

class MusicBrainz:

    def __init__(self):
        musicbrainzngs.set_useragent("Roadie", "0.1", "https://github.com/sphildreth/roadie")
        self.artists = {}
        self.searchReleases = {}
        self.releases = {}

    def lookupArtist(self, name):
        cacheKey = name.replace(" ", "")
        if cacheKey in self.artists:
            return self.artists[cacheKey]

        try:
            print("Getting Artist [" + name + "] From MusicBrainz")
            result = musicbrainzngs.search_artists(artist=name, type="group")
        except:
            result = None

        if result and result['artist-list'][0]:
            self.artists[cacheKey] = result['artist-list'][0]
            return self.artists[cacheKey]


    def searchForRelease(self, artistId, title):
        cacheKey = artistId + "." + title.replace(" ", "")
        if cacheKey in self.searchReleases:
            return self.searchReleases[cacheKey]

        try:
            print("Search For Release [" + title + "] From MusicBrainz")
            result = musicbrainzngs.search_releases(limit=1, arid=artistId, release=title)
        except:
            result = None

        if result and result['release-list'][0]:
            self.searchReleases[cacheKey] = result['release-list'][0]
            return self.searchReleases[cacheKey]


    def lookupRelease(self, releaseId):
        if releaseId in self.releases:
            return self.releases[releaseId]

        try:
            print("Getting Release [" + releaseId + "] From MusicBrainz")
            result = musicbrainzngs.get_release_by_id(releaseId, includes=['recordings'])
        except:
            result = None

        if result:
            self.releases[releaseId] = result['release']
            return self.releases[releaseId]

    def tracksForRelease(self, relasedId):
        release = self.lookupRelease(relasedId)
        if release:
            return release['medium-list']


    def lookupCoverArt(self, releaseId):
        try:
            return musicbrainzngs.get_image_front(releaseId)
        except:
            return None
