from flask import jsonify
from flask_restful import Resource, reqparse
from sqlalchemy.sql import text, func

from resources.models.Artist import Artist
from resources.models.Playlist import Playlist, PlaylistTrack
from resources.models.Track import Track
from resources.models.ReleaseMedia import ReleaseMedia
from resources.models.Release import Release


class PlaylistTrackListApi(Resource):
    def __init__(self, **kwargs):
        self.dbConn = kwargs['dbConn']
        self.dbSession = kwargs['dbSession']
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('playListId', type=int)
        self.reqparse.add_argument('current', type=int)
        self.reqparse.add_argument('limit', type=int)
        self.reqparse.add_argument('skip', type=int)
        self.reqparse.add_argument('filter', type=str)
        self.reqparse.add_argument('sort', type=str)
        self.reqparse.add_argument('order', type=str)
        super(PlaylistTrackListApi, self).__init__()

    def get(self):
        args = self.reqparse.parse_args()
        playListId = args.playListId
        get_current = args.current
        get_limit = args.limit or 25
        get_skip = args.skip or 0
        sort = args.sort or 'title'
        order = args.order or 'asc'
        if get_current:
            get_skip = (get_current * get_limit) - get_limit

        listFilter = ""
        if args.filter:
            listFilter = "AND (t.title LIKE '%" + args.filter + "%' " \
                         " OR r.title LIKE '%" + args.filter + "%' " \
                         " OR a.name LIKE '%" + args.filter + "%') "
        t = text("SELECT COUNT(1) "
                 "FROM `playlisttrack` plt "
                 "JOIN `playlist` pl ON (pl.id = plt.playListId) "
                 "JOIN `track` t ON (t.id = plt.trackId) "
                 "JOIN `releasemedia` rm ON (rm.id = t.releaseMediaId) "
                 "JOIN `release` r ON (r.id = rm.releaseId) "
                 "JOIN `artist` a ON (a.id = r.artistId) "
                 "WHERE (plt.playListId = " + str(playListId) + ") " + listFilter +
                 ";")
        total_records = self.dbConn.execute(t).scalar()
        rows = []
        t = text("SELECT plt.roadieId, t.roadieId as trackId, t.title, r.roadieId as releaseId, r.title as releaseTitle, "
                 " r.releaseDate as releaseDate, a.roadieId as artistId, a.name as artistName, r.rating, "
                 " ut.rating as userRating "
                 "FROM `playlisttrack` plt "
                 "JOIN `playlist` pl on (pl.id = plt.playListId) "
                 "JOIN `track` t on (t.id = plt.trackId) "
                 "JOIN `releasemedia` rm on (rm.id = t.releaseMediaId) "
                 "JOIN `release` r on (r.id = rm.releaseId) "
                 "JOIN `artist` a on (a.id = r.artistId) "
                 "LEFT JOIN `usertrack` ut ON (ut.trackId = t.id AND ut.userId = pl.userId) "
                 "WHERE (plt.playListId = " + str(playListId) + ") " + listFilter +
                 "ORDER BY " + sort + " " + order + " "
                 "LIMIT " + str(get_skip) + "," + str(get_limit) + ";")
        for row in self.dbConn.execute(t):
            rows.append({
                "id": row.roadieId,
                "artistId": row.artistId,
                "artistName": row.artistName,
                "releaseId": row.releaseId,
                "releaseDate": row.releaseDate.isoformat(),
                "releaseYear": row.releaseDate.strftime('%Y'),
                "releaseTitle": row.releaseTitle,
                "trackId": row.trackId,
                "title": row.title,
                "rating": row.rating,
                "userRating": row.userRating
            })

        return jsonify(rows=rows, current=args.current or 1, rowCount=len(rows), total=total_records, message="OK")
