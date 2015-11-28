import io
import math
from flask import request


class M3U(object):
    @staticmethod
    def generate(trackInfos):
        m3u = io.StringIO()
        m3u.write("#EXTM3U\n\n")
        for trackInfo in trackInfos:
            m3u.write(
                "#EXTINF:" + trackInfo['Length'] + "," + trackInfo['ArtistName'] + " - " + trackInfo['Title'] + "\n")
            m3u.write(trackInfo['StreamUrl'] + "\n")
        m3u.write("#EXT-X-ENDLIST\n")
        return io.BytesIO(str.encode(m3u.getvalue()))

    @staticmethod
    def makeTrackInfo(user, release, track):
        if not user or not release or not track:
            return None
        return {
            'Length': str(math.ceil(track.duration)),
            'ArtistId': str(release.artist.roadieId) if not track.artist else str(track.artist.roadieId),
            'ArtistName': release.artist.name if not track.artist else track.artist.name,
            'ReleaseMediaNumber': track.releasemedia.releaseMediaNumber,
            'ReleaseTitle': release.title,
            'ReleaseYear': release.releaseDate.strftime('%Y'),
            'TrackNumber': track.trackNumber,
            'Title': track.title,
            'ReleaseId': str(release.roadieId),
            'UserId': str(user.roadieId),
            'TrackId': str(track.roadieId),
            'StreamUrl': request.url_root + "stream/track/" + str(user.roadieId) + "/" + str(track.roadieId)
        }
