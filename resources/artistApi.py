from flask_restful import abort, Resource, reqparse

from resources.models.Artist import Artist


class ArtistApi(Resource):

    artist = None

    def __init__(self, **kwargs):
        self.dbConn = kwargs['dbConn']
        self.dbSession = kwargs['dbSession']
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('inc', type=str)

    def abort_if_artist_doesnt_exist(self, artistId):
        self.artist = self.dbSession.query(Artist).filter(Artist.roadieId == artistId).first()
        if not self.artist:
            abort(404, message="Artist {} doesn't exist".format(artistId))

    def get(self, artistId):
        self.abort_if_artist_doesnt_exist(artistId)
        args = self.reqparse.parse_args()
        includes = args.inc or 'releases,tracks'
        return self.artist.serialize(includes)




