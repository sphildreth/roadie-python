import datetime
from flask_restful import Resource, reqparse
from flask import jsonify



class ReleaseListApi(Resource):

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('current', type=int)
        self.reqparse.add_argument('limit', type=int)
        self.reqparse.add_argument('skip', type=int)
        self.reqparse.add_argument('filter', type=str)
        self.reqparse.add_argument('inc', type=str)
        self.reqparse.add_argument('sort', type=str)
        self.reqparse.add_argument('order', type=str)
        super(ReleaseListApi, self).__init__()

    def get(self):
        args = self.reqparse.parse_args()
        get_current = args.current or 1
        get_limit = args.limit or 10
        get_skip = args.skip or 0
        includes = args.inc or 'tracks'
        sort = args.sort or 'ReleasedDate'
        if sort == "Year":
            sort = "ReleaseDate"
        if sort == "ArtistName":
            sort = "Artist__Name"
        order = args.order or 'asc'
        if order != 'asc':
            order = "-"
        else:
            order = ""
        if get_current:
            get_skip = (get_current * get_limit) - get_limit
        connect()
        if args.filter:
            releases = Release.objects(__raw__= {'$or' : [
                { 'Title' : { '$regex' : args.filter, '$options': 'mi' }},
                { 'AlternateNames': { '$regex' : args.filter, '$options': 'mi' } }
            ]}).order_by(order + sort)[get_skip:get_limit]
        else:
            releases = Release.objects().order_by(order + sort)[:get_limit]

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
                    "ArtistId" : str(release.Artist.id),
                    "Year": release.ReleaseDate,
                    "ArtistName": release.Artist.Name,
                    "Title": release.Title,
                    "Tracks": trackInfo,
                    "TrackCount": release.TrackCount,
                    "ReleasePlayedCount": 0,
                    "LastUpdated": release.LastUpdated.strftime("%Y-%m-%d %H:%M"),
                    "Rating": release.Rating or 0,
                    "ThumbnailUrl": "/images/release/thumbnail/" + str(release.id)
                })

        return jsonify(rows=rows, current=args.current or 1, rowCount=len(rows), total=releases.count(), message="OK")
