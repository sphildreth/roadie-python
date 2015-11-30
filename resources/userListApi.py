import datetime
from flask_restful import Resource, reqparse
from flask import jsonify
from resources.models.User import User
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Integer, desc, String, update
from sqlalchemy.sql import text, func


class UserListApi(Resource):
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
        super(UserListApi, self).__init__()

    def get(self):
        args = self.reqparse.parse_args()
        get_current = args.current
        get_limit = args.limit or 10
        get_skip = args.skip or 0
        sort = args.sort or 'username'
        order = args.order or 'asc'
        if order != 'asc':
            order = "-"
        else:
            order = ""
        if get_current:
            get_skip = (get_current * get_limit) - get_limit
        if args.filter:
            total_records = self.dbSession.query(func.count(User.id)).\
                filter(User.username.like("%" + args.filter + "%")).scalar()
            users = self.dbSession.query(User).filter(User.username.like("%" + args.filter + "%")) \
                .order_by(order + sort).slice(get_skip, get_skip + get_limit)
        else:
            total_records = self.dbSession.query(func.count(User.id)).scalar()
            users = self.dbSession.query(User).order_by(order + sort).slice(get_skip, get_skip + get_limit)

        rows = []
        if users:
            for user in users:
                rows.append({
                    "userId": user.roadieId,
                    "username": user.username,
                    "email": user.email,
                    "createdDate": user.createdDate.isoformat(),
                    "lastUpdated": "" if not user.lastUpdated else user.lastUpdated.isoformat(),
                    "avatarlUrl": "/images/user/avatar/" + user.roadieId
                })

        return jsonify(rows=rows, current=args.current or 1, rowCount=len(rows), total=total_records, message="OK")
