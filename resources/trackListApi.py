import datetime
from flask_restful import Resource, reqparse
from flask import jsonify
from mongoengine import connect
from resources.mongoModels import Artist, Release, Track


class TrackListApi(Resource):

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('current', type=int)
        self.reqparse.add_argument('limit', type=int)
        self.reqparse.add_argument('skip', type=int)
        self.reqparse.add_argument('filter', type=str)
        self.reqparse.add_argument('inc', type=str)
        super(TrackListApi, self).__init__()

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
            tracks = Track.objects(Title__icontains = args.filter)[get_skip:get_limit]
        else:
            tracks = Track.objects()[:get_limit]

        rows = []
        if tracks:
            for track in tracks:
                for release in Release.objects(Tracks__Track=track):
                    for rt in release.Tracks:
                        if rt.Track.id == track.id:
                            rows.append({
                                "ReleaseId": str(release.id),
                                "TrackId": str(track.id),
                                "Year": release.ReleaseDate,
                                "Title": release.Artist.Name + " - " + release.Title + " - " + track.Title,
                                "ThumbnailUrl": "/images/release/thumbnail/" + str(release.id)
                            })
                            break

        return jsonify(rows=rows, current=args.current or 1, rowCount=len(rows), total=tracks.count(), message="OK")
