from flask_restful import abort, Resource, reqparse
from flask import jsonify
from resources.models.User import User
from resources.models.UserTrack import UserTrack

from sqlalchemy.sql import func


class UserApi(Resource):
    user = None

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
        self.reqparse.add_argument('inc', type=str)

    def abort_if_user_doesnt_exist(self, artistId):
        self.user = self.dbSession.query(User).filter(User.roadieId == artistId).first()
        if not self.user:
            abort(404, message="User {} doesn't exist".format(artistId))

    def get(self, userId):
        self.abort_if_user_doesnt_exist(userId)
        args = self.reqparse.parse_args()
        includes = args.inc or 'stats,thumbnails'
        return self.user.serialize(includes)

    def playhistory(self, args):
        get_current = args.current
        get_limit = args.limit or 25
        get_skip = args.skip or 0
        sort = args.sort or 'lastPlayed'
        order = args.order or 'asc'
        includes = args.inc or 'stats,thumbnails'
        if order != 'asc':
            order = "-"
        else:
            order = ""
        if get_current:
            get_skip = (get_current * get_limit) - get_limit
        if args.filter:
            total_records = self.dbSession \
                .query(func.count(UserTrack.id)) \
                .filter(UserTrack.track.like("%" + args.filter + "%")).scalar()
            tracks = self.dbSession.query(UserTrack).filter(UserTrack.userId == self.user.id).filter(
                UserTrack.track.title.like("%" + args.filter + "%")) \
                .order_by(order + sort).slice(get_skip, get_skip + get_limit)
        else:
            total_records = self.dbSession.query(func.count(UserTrack.id)).scalar()
            tracks = self.dbSession.query(UserTrack).filter(UserTrack.userId == self.user.id).order_by(
                order + sort).slice(get_skip, get_skip + get_limit)
        rows = []
        if tracks:
            for track in tracks:
                rows.append({
                    'userTrack': track.serialize(includes),
                    'track': track.track.serialize(includes)
                })

