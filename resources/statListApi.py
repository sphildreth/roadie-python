from flask import jsonify
from flask_restful import Resource
from sqlalchemy.sql import func

from resources.models.Artist import Artist


class StatListApi(Resource):
    def __init__(self, **kwargs):
        self.dbConn = kwargs['dbConn']
        self.dbSession = kwargs['dbSession']
        super(StatListApi, self).__init__()

    def get(self):
        rows = [self.statArtistReleaseCount()]
        return jsonify(rows=rows, rowCount=len(rows), message="OK")

    def statArtistReleaseCount(self):
        artistAverageCount = self.dbSession.query(func.avg(Artist.releases))
        artistMinimumCount = self.dbSession.query(func.min(Artist.releases)).scalar()
        artistMaximumCount = self.dbSession.query(func.max(Artist.releases)).scalar()
        artistMaximumId = ''
        artistMaxName = ''

        return {
            'title': 'Artist Release Count',
            'class': 'fa-user',
            'average': {
                'type': 'string',
                'value': artistAverageCount,
                'detail': {
                    'text': ''
                }
            },
            'minimum': {
                'type': 'string',
                'value': artistMinimumCount,
                'detail': {
                    'text': 'Many'
                }
            },
            'maximum': {
                'type': 'artist',
                'value': artistMaximumCount,
                'detail': {
                    'id': artistMaximumId,
                    'thumbnailUrl': '/images/artist/thumbnail/' + artistMaximumId,
                    'detailUrl': '/artist/' + artistMaximumId,
                    'text': artistMaxName
                }
            }
        }
