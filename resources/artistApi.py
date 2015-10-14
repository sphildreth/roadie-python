from flask_restful import Resource
from flask import jsonify
from resources.mongoModels import Artist

class ArtistApi(Resource):

    def get(self, artist_id):
        # artist = db.artists.find_one({'_id': uuid.UUID(artist_id)})
        artist = {}
        return jsonify(data=artist, message="OK")

    def put(self, artist_id):
        pass

    def delete(self, artist_id):
        pass

    def getThumbnail(self, artist_id):
        artist = Artist.objects(id=artist_id).first()
        return artist.Thumbnail.read()
