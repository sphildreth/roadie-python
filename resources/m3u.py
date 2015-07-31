import io
import math
from flask import request

class M3U(object):
    @staticmethod
    def generate(tracks):
        m3u = io.StringIO()
        m3u.write("#EXTM3U\n\n")
        for track in tracks:
            m3u.write("#EXTINF:" + str(math.ceil(track.Length)) + "," + track.Artist.Name + " - " + track.Title + "\n")
            m3u.write(request.url_root + "stream/track/" + str(track.id) + "\n")
        m3u.write("#EXT-X-ENDLIST\n")
        return io.BytesIO(str.encode(m3u.getvalue()))
