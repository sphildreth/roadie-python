from flask_restful import abort, Resource, reqparse

from resources.models.Release import Release


class ReleaseApi(Resource):

    release = None

    def __init__(self, **kwargs):
        self.dbConn = kwargs['dbConn']
        self.dbSession = kwargs['dbSession']
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('inc', type=str)

    def abort_if_release_doesnt_exist(self, artistId):
        self.release = self.dbSession.query(Release).filter(Release.roadieId == artistId).first()
        if not self.release:
            abort(404, message="Release {} doesn't exist".format(artistId))

    def get(self, releaseId):
        self.abort_if_release_doesnt_exist(releaseId)
        args = self.reqparse.parse_args()
        includes = args.inc or 'labels,stats,tracks'
        return self.release.serialize(includes, self.dbConn)




