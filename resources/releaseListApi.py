import datetime
from flask_restful import Resource, reqparse
from flask import jsonify
from resources.models.Artist import Artist
from resources.models.Track import Track
from resources.models.Release import Release
from resources.models.ReleaseMedia import ReleaseMedia
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Integer, desc, String, update
from sqlalchemy.sql import text, func


class ReleaseListApi(Resource):
    def __init__(self, **kwargs):
        self.dbConn = kwargs['dbConn']
        self.dbSession = kwargs['dbSession']
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
        get_limit = args.limit or 25
        get_skip = args.skip or 0
        includes = args.inc or 'tracks'
        sort = args.sort or 'releaseDate'
        order = args.order or 'asc'
        total_records = 0

        if sort == "releaseYear":
            sort = "releaseDate"

        if get_current:
            get_skip = (get_current * get_limit) - get_limit

        if args.filter:
            name = args.filter.lower().strip().replace("'", "''")
            stmt = text("lower(release.title) = '" + name + "' " +
                        "OR lower(release.title) LIKE '%" + name + "%' " +
                        "OR (lower(alternateNames) LIKE '%" + name + "%' " + ""
                        " OR alternateNames LIKE '" + name + "|%' " +
                        " OR alternateNames LIKE '%|" + name + "|%' " +
                        " OR alternateNames LIKE '%|" + name + "')"
                        )

            total_records = self.dbSession.query(func.count(Release.id)).filter(stmt).scalar()
            releases = self.dbSession.query(Release).filter(stmt) \
                .order_by(text(sort + " " + order)).slice(get_skip, get_limit)
        else:
            total_records = self.dbSession.query(func.count(Release.id)).scalar()
            releases = self.dbSession.query(Release).join(Artist, Artist.id == Release.artistId).order_by(text(sort + " " + order)).limit(get_limit)
        rows = []
        if releases:
            for release in releases:
                trackCount = 0
                trackInfo = []
                if 'tracks' in includes:
                    for media in release.media:
                        for track in media.tracks:
                            trackLength = datetime.timedelta(seconds=track.duration)
                            trackInfo.append({
                                "trackId": str(track.roadieId),
                                "trackNumber": track.trackNumber,
                                "releaseMediaNumber": media.releaseMediaNumber,
                                "length": ":".join(str(trackLength).split(":")[1:3]),
                                "duration": track.duration,
                                "title": track.title
                            })
                else:
                    trackCount = self.dbSession.query(func.sum(ReleaseMedia.trackCount)).filter(
                        ReleaseMedia.releaseId == release.id).scalar()
                rows.append({
                    "id": release.roadieId,
                    "artistId": release.artist.roadieId,
                    "releaseDate": "" if not release.releaseDate else release.releaseDate.isoformat(),
                    "releaseYear": "----" if not release.releaseDate else release.releaseDate.strftime('%Y'),
                    "artist.name": release.artist.name,
                    "title": release.title,
                    "tracks": trackInfo,
                    "trackCount": len(trackInfo) if trackInfo else int(trackCount or 0),
                    "releasePlayedCount": 0,
                    "release.createdDate": release.createdDate.isoformat(),
                    "release.lastUpdated": "" if not release.lastUpdated else release.lastUpdated.isoformat(),
                    "release.rating": release.rating or 0,
                    "thumbnailUrl": "/images/release/thumbnail/" + release.roadieId
                })

        return jsonify(rows=rows, current=args.current or 1, rowCount=len(rows), total=total_records, message="OK")
