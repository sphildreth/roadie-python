import datetime
from flask_restful import Resource, reqparse
from flask import jsonify
from resources.models.Artist import Artist
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func, and_, or_, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Integer, desc, String, update
from sqlalchemy.sql import text, func


class ArtistListApi(Resource):
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

    def get(self):
        args = self.reqparse.parse_args()
        get_current = args.current or 1
        get_limit = args.limit or 20
        get_skip = args.skip or 0
        includes = args.inc or 'releases,tracks'
        sort = args.sort or 'sortName'
        order = args.order or 'asc'
        total_records = 0

        if get_current:
            get_skip = (get_current * get_limit) - get_limit

        if args.filter:
            name = args.filter.lower().strip().replace("'", "''")
            stmt = text("lower(artist.name) = '" + name + "' " +
                        "OR lower(artist.name) LIKE '%" + name + "%' " +
                        "OR lower(artist.sortName) LIKE '%" + name + "%' " +
                        "OR (lower(alternateNames) LIKE '%" + name + "%' " + ""
                        " OR alternateNames LIKE '" + name + "|%' " +
                        " OR alternateNames LIKE '%|" + name + "|%' " +
                        " OR alternateNames LIKE '%|" + name + "')"
                        )
            total_records = self.dbSession.query(func.count(Artist.id)).filter(stmt).scalar()
            artists = self.dbSession.query(Artist).filter(stmt) \
                .order_by(text(sort + " " + order)).slice(get_skip, get_limit)
        else:
            total_records = self.dbSession.query(func.count(Artist.id)).scalar()
            artists = self.dbSession.query(Artist).order_by(text(sort + " " + order)).slice(get_skip, get_limit)
        rows = []
        if artists:
            for artist in artists:
                releaseInfo = []
                if 'releases' in includes:
                    for release in artist.releases:
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
                        releaseInfo.append({
                            "releaseId": str(release.roadieId),
                            "releaseDate": release.releaseDate.isoformat(),
                            "releaseYear": release.releaseDate.strftime('%Y'),
                            "title": release.title,
                            "tracks": trackInfo,
                            "thumbnailUrl": "/images/release/thumbnail/" + str(release.roadieId)
                        })
                artistTrackCount = self.dbConn.execute(text(
                    "select COUNT(t.id) as trackCount " +
                    "from `artist` a " +
                    "join `release` r on r.artistId = a.id " +
                    "join `releasemedia` rm on rm.releaseId  = r.id " +
                    "join `track` t on t.releaseMediaId = rm.id " +
                    "where a.id =" + str(artist.id) + ";", autocommit=True).columns(trackCount=Integer)).fetchone()
                rows.append({
                    "name": artist.name,
                    "id": str(artist.roadieId),
                    "rating": str(artist.rating or 0),
                    "artistReleaseCount": len(artist.releases),
                    "artistTrackCount": artistTrackCount[0],
                    "createdDate": artist.createdDate.isoformat(),
                    "lastUpdated": "" if not artist.lastUpdated else artist.lastUpdated.isoformat(),
                    "artistPlayedCount": 0,
                    "releases": releaseInfo,
                    "thumbnailUrl": "/images/artist/thumbnail/" + str(artist.roadieId)
                })

        return jsonify(rows=rows, current=args.current or 1, rowCount=len(rows), total=total_records, message="OK")
