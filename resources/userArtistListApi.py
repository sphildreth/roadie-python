from flask_restful import abort, Resource, reqparse
from flask import jsonify
from resources.models.User import User
from resources.models.UserArtist import UserArtist

from sqlalchemy.sql import func


class UserArtistListApi(Resource):
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
        get_current = args.current
        get_limit = args.limit or 25
        get_skip = args.skip or 0
        sort = args.sort or 'userartist.lastUpdated'
        order = args.order or 'desc'
        if userId:
            self.abort_if_user_doesnt_exist(userId)
        includes = args.inc or 'artist,thumbnails'
        if order != 'asc':
            order = "-"
        else:
            order = ""
        if get_current:
            get_skip = (get_current * get_limit) - get_limit
        if args.filter:
            total_records = self.dbSession \
                .query(func.count(UserArtist.id)) \
                .filter(UserArtist.userId == self.user.id) \
                .filter(UserArtist.artist.name.like("%" + args.filter + "%")) \
                .scalar()
            artists = self.dbSession \
                .query(UserArtist) \
                .filter(UserArtist.userId == self.user.id) \
                .filter(UserArtist.artist.name.like("%" + args.filter + "%")) \
                .order_by(order + sort) \
                .slice(get_skip, get_skip + get_limit)
        else:
            q = self.dbSession \
                .query(UserArtist) \
                .filter(UserArtist.userId == self.user.id) \
                .order_by(order + sort)

            total_records_q = q.statement.with_only_columns([func.count(UserArtist.id)]).order_by(None).group_by(
                UserArtist.userId)
            total_records = q.session.execute(total_records_q).scalar()

            artists = self.dbSession \
                .query(UserArtist) \
                .filter(UserArtist.userId == self.user.id) \
                .order_by(order + sort) \
                .slice(get_skip, get_skip + get_limit)
        rows = []
        if artists:
            for track in artists:
                rows.append(track.serialize(includes, self.dbConn))
        return jsonify(rows=rows, current=args.current or 1, rowCount=len(rows), total=total_records, message="OK")
