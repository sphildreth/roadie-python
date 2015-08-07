import io
import math
from flask import request

class M3U(object):
    @staticmethod
    def generate(trackInfos):
        m3u = io.StringIO()
        m3u.write("#EXTM3U\n\n")
        for trackInfo in trackInfos:
            m3u.write("#EXTINF:" + trackInfo['Length'] + "," + trackInfo['ArtistName'] + " - " + trackInfo['Title'] + "\n")
            m3u.write(request.url_root + "stream/track/" + trackInfo['UserId'] + "/" + trackInfo['ReleaseId'] + "/" + trackInfo['TrackId'] + "\n")
        m3u.write("#EXT-X-ENDLIST\n")
        return io.BytesIO(str.encode(m3u.getvalue()))

    @staticmethod
    def makeTrackInfo(user, release, track):
        return {
            'Length': str(math.ceil(track.Length)),
            'ArtistName': track.Artist.Name,
            'Title': track.Title,
            'ReleaseId': str(release.id),
            'UserId': str(user.id),
            'TrackId': str(track.id)
        }