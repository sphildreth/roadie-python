import datetime
from flask_restful import Resource, reqparse
from flask import jsonify
from resources.models.Track import Track
from resources.models.UserTrack import UserTrack
from resources.models.Release import Release
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Integer, desc, String, update
from sqlalchemy.sql import text, func


class TrackListApi(Resource):
    def __init__(self, **kwargs):
        self.dbConn = kwargs['dbConn']
        self.dbSession = kwargs['dbSession']
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('current', type=int)
        self.reqparse.add_argument('limit', type=int)
        self.reqparse.add_argument('skip', type=int)
        self.reqparse.add_argument('filter', type=str)
        self.reqparse.add_argument('sort', type=str)
        self.reqparse.add_argument('order', type=str)
        self.reqparse.add_argument('userId', type=str)
        super(TrackListApi, self).__init__()

    def get(self):
        args = self.reqparse.parse_args()
        get_current = args.current
        get_limit = args.limit or 25
        get_skip = args.skip or 0
        sort = args.sort or 'title'
        order = args.order or 'asc'
        if order != 'asc':
            order = "-"
        else:
            order = ""
        if get_current:
            get_skip = (get_current * get_limit) - get_limit
        if args.filter:
            total_records = self.dbSession\
                .query(func.count(Track.id))\
                .filter(Track.title.like("%" + args.filter + "%")).scalar()
            tracks = self.dbSession.query(Track).filter(Track.title.like("%" + args.filter + "%")) \
                .order_by(order + sort).slice(get_skip, get_skip + get_limit)
        else:
            total_records = self.dbSession.query(func.count(Track.id)).scalar()
            tracks = self.dbSession.query(Track).order_by(order + sort).slice(get_skip, get_skip + get_limit)
        rows = []
        if tracks:
            for track in tracks:
                release = track.releasemedia.release
                rows.append({
                    "id": track.roadieId,
                    "releaseId": release.roadieId,
                    "releaseDate": release.releaseDate.isoformat(),
                    "releaseYear": release.releaseDate.strftime('%Y'),
                    "title": release.artist.name + " - " + release.title + " - " + track.title,
                    "thumbnailUrl": "/images/release/thumbnail/" + release.roadieId
                })

        return jsonify(rows=rows, current=args.current or 1, rowCount=len(rows), total=total_records, message="OK")
