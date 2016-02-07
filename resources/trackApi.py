from flask_restful import abort, Resource, reqparse

from resources.models.Track import Track


class TrackApi(Resource):

    track = None

    def __init__(self, **kwargs):
        self.dbConn = kwargs['dbConn']
        self.dbSession = kwargs['dbSession']
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('inc', type=str)

    def abort_if_track_doesnt_exist(self, artistId):
        self.track = self.dbSession.query(Track).filter(Track.roadieId == artistId).first()
        if not self.track:
            abort(404, message="Track {} doesn't exist".format(artistId))

    def get(self, trackId):
        self.abort_if_track_doesnt_exist(trackId)
        args = self.reqparse.parse_args()
        includes = args.inc
        return self.track.serialize(includes)




