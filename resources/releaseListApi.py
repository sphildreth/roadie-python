import datetime
from flask_restful import Resource, reqparse
from flask import jsonify
from mongoengine import connect
from resources.models import Artist, Release


class ReleaseListApi(Resource):

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('current', type=int)
        self.reqparse.add_argument('limit', type=int)
        self.reqparse.add_argument('skip', type=int)
        self.reqparse.add_argument('filter', type=str)
        self.reqparse.add_argument('inc', type=str)
        super(ReleaseListApi, self).__init__()

    def get(self):
        args = self.reqparse.parse_args()
        get_current = args.current or 1
        get_limit = args.limit or 10
        get_skip = args.skip or 0
        includes = args.inc or 'tracks'
        if get_current:
            get_skip = (get_current * get_limit) - get_limit
        connect()
        if args.filter:
            releases = Release.objects(Title__icontains = args.filter)[get_skip:get_limit]
        else:
            releases = Release.objects()[:get_limit]

        rows = []
        if releases:
            for release in releases:
                trackInfo = []
                if 'tracks' in includes:
                    for track in release.Tracks:
                        trackLength = 0
                        if track:
                            trackLength = datetime.timedelta(seconds=track.Track.Length);
                        trackInfo.append({
                            "TrackId": str(track.Track.id),
                            "TrackNumber": track.TrackNumber,
                            "ReleaseMediaNumber": track.ReleaseMediaNumber,
                            "Length": ":".join(str(trackLength).split(":")[1:3]),
                            "Title": track.Track.Title
                        })
                rows.append({
                    "ReleaseId": str(release.id),
                    "Year": release.ReleaseDate,
                    "Title": release.Title,
                    "Tracks": trackInfo,
                    "ThumbnailUrl": "/images/release/thumbnail/" + str(release.id)
                })

        return jsonify(rows=rows, current=args.current or 1, rowCount=len(rows), total=releases.count(), message="OK")