import io
import os
import hashlib
import json
import random
import zipfile
import uuid
from time import time
from operator import itemgetter
from re import findall

from urllib.parse import urlparse, urljoin

from PIL import Image as PILImage
from flask import Flask, jsonify, render_template, send_file, Response, request, session, \
    flash, url_for, redirect, g
import flask_admin as admin
from flask_restful import Api
from flask_session import Session as FlaskSession
from tornado.wsgi import WSGIContainer
from tornado.web import Application, FallbackHandler
from tornado.websocket import WebSocketHandler
from tornado.ioloop import IOLoop
from werkzeug.datastructures import Headers
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy import create_engine, Integer, desc
from sqlalchemy.sql import text, func

from importers.collectionImporter import CollectionImporter
from resources.common import *
from resources.models.Artist import Artist
from resources.models.Genre import Genre
from resources.models.Collection import Collection
from resources.models.Image import Image
from resources.models.Label import Label
from resources.models.Release import Release
from resources.models.ReleaseLabel import ReleaseLabel
from resources.models.ReleaseMedia import ReleaseMedia
from resources.models.Playlist import Playlist
from resources.models.Track import Track
from resources.models.User import User
from resources.models.UserArtist import UserArtist
from resources.models.UserRelease import UserRelease
from resources.models.UserRole import UserRole
from resources.models.UserTrack import UserTrack
from resources.artistListApi import ArtistListApi
from searchEngines.imageSearcher import ImageSearcher
from resources.releaseListApi import ReleaseListApi
from resources.trackListApi import TrackListApi
from resources.processor import Processor
from resources.logger import Logger
from resources.id3 import ID3
from resources.m3u import M3U
from resources.validator import Validator
from flask.ext.login import LoginManager, login_user, logout_user, \
    current_user, login_required
from flask.ext.bcrypt import Bcrypt
from resources.nocache import nocache
from resources.jinjaFilters import format_tracktime, format_timedelta, calculate_release_tracks_Length, \
    group_release_tracks_filepaths, format_age_from_date, calculate_release_discs, count_new_lines
from viewModels.RoadieModelView import RoadieModelView, RoadieModelAdminRequiredView
from viewModels.RoadieReleaseModelView import RoadieReleaseModelView
from viewModels.RoadieCollectionModelView import RoadieCollectionModelView
from viewModels.RoadieUserArtistModelView import RoadieUserArtistModelView
from viewModels.RoadieUserReleaseModelView import RoadieUserReleaseModelView
from viewModels.RoadieUserTrackModelView import RoadieUserTrackModelView
from viewModels.RoadieArtistModelView import RoadieArtistModelView
from viewModels.RoadiePlaylistModelView import RoadiePlaylistModelView

clients = []

app = Flask(__name__)

app.jinja_env.filters['format_tracktime'] = format_tracktime
app.jinja_env.filters['format_timedelta'] = format_timedelta
app.jinja_env.filters['calculate_release_tracks_Length'] = calculate_release_tracks_Length
app.jinja_env.filters['group_release_tracks_filepaths'] = group_release_tracks_filepaths
app.jinja_env.filters['format_age_from_date'] = format_age_from_date
app.jinja_env.filters['calculate_release_discs'] = calculate_release_discs
app.jinja_env.filters['count_new_lines'] = count_new_lines

with open(os.path.join(app.root_path, "settings.json"), "r") as rf:
    config = json.load(rf)
app.config.update(config)

thumbnailSize = config['ROADIE_THUMBNAILS']['Height'], config['ROADIE_THUMBNAILS']['Width']
siteName = config['ROADIE_SITE_NAME']
trackPathReplace = None
if 'ROADIE_TRACK_PATH_REPLACE' in config:
    trackPathReplace = config['ROADIE_TRACK_PATH_REPLACE']
avatarSize = 30, 30

engine = create_engine(config['ROADIE_DATABASE_URL'])
conn = engine.connect()
Base = declarative_base()
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
dbSession = DBSession()

userCache = dict()

flask_bcrypt = Bcrypt(app)
bcrypt = Bcrypt()
api = Api(app)

FlaskSession(app)

logger = Logger()


def getUser(userId=None):
    """
    Cache the user to reduce DB hits
    :param userId: str
    :rtype : User
    :return: Return user for Current logged in user cache enabled
    """
    userId = userId or getUserId()
    if userId not in userCache:
        userCache[userId] = dbSession.query(User).filter(User.roadieId == userId).first()
    return userCache[userId]


def getUserId():
    """
    Return the UserId for the Curent user
    :return: str
    """
    return current_user.roadieId


def getArtist(artistId):
    """
    Abstract the fetch artist from DB and include any UserArtist
    :param artistId: str
    :return: Artist
    """
    return dbSession.query(Artist) \
        .filter(Artist.roadieId == artistId) \
        .first()


def getRelease(releaseId):
    """
    Abstract the fetch release from DB and include any UserRelease
    :param releaseId: str
    :return: Release
    """
    return dbSession.query(Release) \
        .filter(Release.roadieId == releaseId) \
        .first()


def getTrack(trackId):
    """
    Abstract the fetch Track from DB and include any UserTrack
    :param trackId: str
    :return: Track
    """
    return dbSession.query(Track) \
        .filter(Track.roadieId == trackId) \
        .first()


def pathToTrack(track):
    """
    Adjust the path to a track with any OS or config substitutions
    :param track: Track
    :return: str
    """
    path = os.path.join(config["ROADIE_LIBRARY_FOLDER"], track.filePath)
    if trackPathReplace:
        for rpl in trackPathReplace:
            for key, val in rpl.items():
                path = path.replace(key, val)
    return os.path.join(path, track.fileName)


@app.before_request
def before_request():
    g.siteName = siteName
    g.user = current_user


@app.route('/')
@login_required
def index():
    lastPlayedInfos = []
    for ut in dbSession.query(UserTrack).order_by(desc(UserTrack.lastPlayed))[:35]:
        lastPlayedInfos.append({
            'TrackId': str(ut.track.roadieId),
            'TrackTitle': ut.track.title,
            'ReleaseId': str(ut.track.releasemedia.release.roadieId),
            'ReleaseTitle': ut.track.releasemedia.release.title,
            'ReleaseThumbnail': "/images/release/thumbnail/" + str(ut.track.releasemedia.release.roadieId),
            'ArtistId': str(ut.track.releasemedia.release.artist.roadieId),
            'ArtistName': ut.track.releasemedia.release.artist.name,
            'ArtistThumbnail': "/images/artist/thumbnail/" + str(ut.track.releasemedia.release.artist.roadieId),
            'UserId': str(ut.user.roadieId),
            'Username': ut.user.username,
            'UserThumbnail': "/images/user/avatar/" + str(ut.user.roadieId),
            'UserRating': ut.rating,
            'LastPlayed': arrow.get(ut.lastPlayed).humanize()
        })
    wsRoot = request.url_root.replace("http://", "ws://")
    releases = []
    for r in dbSession.query(Release).order_by(func.random())[:12]:
        releases.append({
            'id': r.roadieId,
            'ArtistName': r.artist.name,
            'Title': r.title,
            'UserRating': 0
        })
    return render_template('home.html', lastPlayedInfos=lastPlayedInfos, wsRoot=wsRoot, releases=releases)


@app.route("/release/setTitle/<roadieId>/<new_title>/<set_tracks_title>/<create_alternate_name>", methods=['POST'])
def setReleaseTitle(roadieId, new_title, set_tracks_title, create_alternate_name):
    release = getRelease(roadieId)
    user = getUser()
    now = arrow.utcnow().datetime
    if not release or not user or not new_title:
        return jsonify(message="ERROR")
    oldTitle = release.Title
    release.Title = new_title
    release.LastUpdated = now
    if create_alternate_name == "true" and new_title not in release.alternateNames:
        release.alternateNames.append(oldTitle)
    dbSession.commit()
    if set_tracks_title == "true":
        for track in release.Tracks:
            trackPath = pathToTrack(track)
            id3 = ID3(trackPath, config)
            id3.updateFromRelease(release, track)
    return jsonify(message="OK")


@app.route("/release/random/<count>", methods=['POST'])
def randomRelease(count):
    try:
        releases = []
        for r in dbSession.query(Release).order_by(func.random())[:count]:
            releases.append({
                'id': r.roadieId,
                'ArtistName': r.artist.name,
                'Title': r.title,
                'UserRating': 0
            })
        return jsonify(message="OK", releases=releases)
    except:
        logger.exception("Error In Release Random")
        return jsonify(message="ERROR")


@app.route("/browseArtists")
@login_required
def browseArtists():
    return render_template('browseArtists.html')


@app.route("/browseReleases")
@login_required
def browseReleases():
    return render_template('browseReleases.html')


@app.route("/randomizer/<type>")
@login_required
def randomizer(type):
    user = getUser()
    if type == "artist":
        artist = dbSession.query(Artist).order_by(func.random()).first()
        return playArtist(artist.id, "0")
    elif type == "release":
        release = dbSession.query(Release).order_by(func.random()).first()
        return playRelease(release.id)
    elif type == "tracks":
        tracks = []
        for track in dbSession.query(Track).order_by(func.random())[:35]:
            t = M3U.makeTrackInfo(user, track.releasemedia.release, track)
            if t:
                tracks.append(t)
        if user.doUseHtmlPlayer:
            session['tracks'] = tracks
            return player()
        return send_file(M3U.generate(tracks),
                         as_attachment=True,
                         attachment_filename="playlist.m3u")


@app.route('/artist/<artist_id>')
@login_required
def artistDetail(artist_id):
    artist = getArtist(artist_id)
    if not artist:
        return render_template('404.html'), 404
    user = getUser()
    userArtist = dbSession.query(UserArtist).filter(UserArtist.userId == user.id).filter(
        UserArtist.artistId == artist.id).first()
    artistSummaries = conn.execute(text(
        "SELECT count(rm.releaseMediaNumber) as releaseMediaCount, count(r.roadieId) as releaseCount, "
        "ts.count, ts.duration, ts.size FROM artist a, (SELECT COUNT(1) as count, sum(t.duration) as duration, "
        "sum(t.fileSize) as size FROM track t join releasemedia rm on rm.id = t.releaseMediaId "
        "join release r on r.id = rm.releaseId "
        "join artist a on a.id = r.artistId "
        "WHERE a.roadieId = '" + artist_id + "') ts "
                                             "join release r on rm.releaseId = r.id "
                                             "join releasemedia rm on rm.releaseId = r.id "
                                             "where a.roadieId = '" + artist_id + "'", autocommit=True)
                                   .columns(trackCount=Integer, releaseMediaCount=Integer, releaseCount=Integer,
                                            releaseTrackTime=Integer, releaseTrackFileSize=Integer)) \
        .fetchone()
    counts = {'tracks': artistSummaries[2], 'releaseMedia': artistSummaries[0], 'releases': artistSummaries[1],
              'length': formatTimeMillisecondsNoDays(artistSummaries[3]), 'fileSize': sizeof_fmt(artistSummaries[4])}
    return render_template('artist.html', artist=artist, releases=artist.releases, counts=counts, userArtist=userArtist)


@app.route("/user/artist/setrating/<artist_id>/<rating>", methods=['POST'])
@login_required
def setUserArtistRating(artist_id, rating):
    try:
        artist = getArtist(artist_id)
        user = getUser()
        if not artist or not user:
            return jsonify(message="ERROR")
        now = arrow.utcnow().datetime
        userArtist = dbSession.query(UserArtist) \
            .filter(UserArtist.id == user.id) \
            .filter(UserArtist.artistId == artist.id).first()
        if not userArtist:
            userArtist = UserArtist()
            userArtist.roadieId = str(uuid.uuid4())
            userArtist.userId = user.id
            userArtist.artistId = artist.id
            dbSession.add(userArtist)
        userArtist.rating = rating
        userArtist.lastUpdated = now
        dbSession.commit()
        # Update artist average rating
        artistAverage = dbSession.query(func.avg(UserArtist.rating)).filter(UserArtist.artistId == artist.id).scalar()
        artist.rating = artistAverage
        artist.lastUpdated = now
        dbSession.commit()
        return jsonify(message="OK", average=artistAverage)
    except:
        logger.exception("Error Setting Artist Rating")
        return jsonify(message="ERROR")


@app.route("/user/artist/toggledislike/<artist_id>/<toggle>", methods=['POST'])
@login_required
def toggleUserArtistDislike(artist_id, toggle):
    try:
        artist = getArtist(artist_id)
        user = getUser()
        if not artist or not user:
            return jsonify(message="ERROR")
        now = arrow.utcnow().datetime
        if not artist.userRatings:
            artist.userRatings = UserArtist()
            artist.userRatings.userId = user.id
            artist.userRatings.artistId = artist.id
        artist.userRatings.IsDisliked = toggle.lower() == "true"
        artist.userRatings.LastUpdated = now
        if artist.userRatings.IsDisliked:
            artist.userRatings.Rating = 0
        dbSession.commit()
        # TODO
        # artistAverage = UserArtist.objects(Artist=artist).aggregate_average('Rating')
        # session.query(func.avg(Rating.field2).label('average')).filter(Rating.url==url_string.netloc)
        artistAverage = 0
        # if userArtist.IsDisliked:
        #     # Update artist average rating
        #      artist.Rating = artistAverage
        #      artist.LastUpdated = now
        #      Artist.save(artist)
        return jsonify(message="OK", average=artistAverage)
    except:
        logger.exception("Error Setting Artist Dislike")
        return jsonify(message="ERROR")


@app.route("/user/artist/togglefavorite/<artist_id>/<toggle>", methods=['POST'])
@login_required
def toggleUserArtistFavorite(artist_id, toggle):
    try:
        # TODO
        # artist = getArtist(artist_id)
        # user = getUser()
        # if not artist or not user:
        #     return jsonify(message="ERROR")
        # if not artist.userRatings:
        #     artist.userRatings = UserArtist()
        #     artist.userRatings.artistId = artist.id
        #     artist.userRatings.userId = user.id
        # artist.userRatings.IsFavorite = toggle.lower() == "true"
        # artist.userRatings.LastUpdated = arrow.utcnow().datetime
        # dbSession.commit()
        return jsonify(message="OK")
    except:
        logger.exception("Error Toggling Favorite")
        return jsonify(message="ERROR")


@app.route("/release/movetrackstocd/<release_id>/<selected_to_cd>", methods=['POST'])
@login_required
def moveTracksToCd(release_id, selected_to_cd):
    release = getRelease(release_id)
    user = getUser()
    if not release or not user:
        return jsonify(message="ERROR")
    releaseMediaNumber = int(selected_to_cd)
    tracksToMove = request.form['tracksToMove']
    now = arrow.utcnow().datetime
    # TODO
    # for trackToMove in tracksToMove.split(','):
    #     for track in release.Tracks:
    #         if str(track.Track.id) == trackToMove:
    #             track.ReleaseMediaNumber = releaseMediaNumber
    #             release.LastUpdated = now
    #             continue
    if release.LastUpdated == now:
        dbSession.commit()
    return jsonify(message="OK")


@app.route("/user/release/setrating/<release_id>/<rating>", methods=['POST'])
@login_required
def setUserReleaseRating(release_id, rating):
    try:
        release = getRelease(release_id)
        user = getUser()
        if not release or not user:
            return jsonify(message="ERROR")
        now = arrow.utcnow().datetime
        userRelease = dbSession.query(UserRelease).filter(UserRelease.userId == user.id).filter(UserRelease.releaseId == release.id).first()
        if not userRelease:
            userRelease = UserRelease()
            userRelease.roadieId = str(uuid.uuid4())
            userRelease.releaseId = release.id
            userRelease.userId = user.id
            dbSession.add(userRelease)
        userRelease.rating = rating
        userRelease.lastUpdated = now
        dbSession.commit()
        releaseAverage = dbSession.query(func.avg(UserRelease.rating)).\
            filter(UserRelease.releaseId == release.id).scalar()
        release.rating = releaseAverage
        release.lastUpdated = now
        dbSession.commit()
        return jsonify(message="OK", average=releaseAverage)
    except:
        logger.exception("Error Settings Release Reating")
        return jsonify(message="ERROR")


@app.route("/user/release/toggledislike/<release_id>/<toggle>", methods=['POST'])
@login_required
def toggleUserReleaseDislike(release_id, toggle):
    try:
        release = getRelease(release_id)
        user = getUser()
        if not release or not user:
            return jsonify(message="ERROR")
        now = arrow.utcnow().datetime
        if not release.userRatings:
            release.userRatings = UserRelease()
            release.userRatings.releaseId = release.id
            release.userRatings.userId = user.id
        release.userRatings.IsDisliked = toggle.lower() == "true"
        release.userRatings.LastUpdated = now
        if release.userRatings.IsDisliked:
            release.userRatings.Rating = 0
        dbSession.commit()
        # TODO
        # releaseAverage = UserRelease.objects(Release=release).aggregate_average('Rating')
        releaseAverage = 0
        # if userRelease.IsDisliked:
        #     # Update release average rating
        #     release.Rating = releaseAverage
        #     release.LastUpdated = now
        #     Release.save(release)
        return jsonify(message="OK", average=releaseAverage)
    except:
        logger.exception("Error Toggling Release Dislike")
        return jsonify(message="ERROR")


@app.route("/user/release/togglefavorite/<release_id>/<toggle>", methods=['POST'])
@login_required
def toggleUserReleaseFavorite(release_id, toggle):
    try:
        release = getRelease(release_id)
        user = getUser()
        if not release or not user:
            return jsonify(message="ERROR")
        if not release.userRatings:
            release.userRatings = UserRelease()
            release.userRatings.releaseId = release.id
            release.userRatings.userId = user.id
        release.userRatings.IsFavorite = toggle.lower() == "true"
        release.userRatings.LastUpdated = arrow.utcnow().datetime
        dbSession.commit()
        return jsonify(message="OK")
    except:
        logger.exception("Error Toggling Release Favorite")
        return jsonify(message="ERROR")


@app.route("/artist/rescan/<artist_id>", methods=['POST'])
@login_required
def rescanArtist(artist_id):
    try:
        artist = getArtist(artist_id)
        if not artist:
            return jsonify(message="ERROR")
        # Update Database with folders found in Library
        processor = Processor(False, True, )
        artistFolder = processor.artistFolder(artist)
        processor.process(folder=artistFolder)
        validator = Validator(False)
        validator.validate(artist)
        return jsonify(message="OK")
    except:
        logger.exception("Error Rescanning Artist")
        return jsonify(message="ERROR")


@app.route("/release/rescan/<release_id>", methods=['POST'])
@login_required
def rescanRelease(release_id):
    try:
        release = getRelease(release_id)
        if not release:
            return jsonify(message="ERROR")
        # Update Database with folders found in Library
        processor = Processor(False, True)
        releaseFolder = processor.albumFolder(release.Artist, release.ReleaseDate[:4], release.Title)
        processor.process(folder=releaseFolder)
        validator = Validator(False)
        validator.validate(release.Artist)
        return jsonify(message="OK")
    except:
        logger.exception("Error Rescanning Release")
        return jsonify(message="ERROR")


@app.route("/release/download/<release_id>")
@login_required
def downloadRelease(release_id):
    release = getRelease(release_id)
    if not release:
        return jsonify(message="ERROR")
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for media in release.media:
            for track in media.tracks:
                mp3File = pathToTrack(track)
                zf.write(mp3File, arcname=track.fileName, compress_type=zipfile.ZIP_DEFLATED)
    memory_file.seek(0)
    zipAttachmentName = release.artist.name + " - " + release.title + ".zip"
    return send_file(memory_file, attachment_filename=zipAttachmentName, as_attachment=True)


@app.route('/artist/delete/<artist_id>', methods=['POST'])
@login_required
def deleteArtist(artist_id):
    artist = getArtist(artist_id)
    if not artist:
        return jsonify(message="ERROR")
    try:
        dbSession.delete(artist)
        return jsonify(message="OK")
    except:
        logger.exception("Error Deleting Artist")
        return jsonify(message="ERROR")


@app.route("/artist/deletereleases/<artist_id>", methods=['POST'])
@login_required
def deleteArtistReleases(artist_id):
    artist = getArtist(artist_id)
    if not artist:
        return jsonify(message="ERROR")
    try:
        # TODO
        # Track.objects(Artist=artist).delete()
        # Release.objects(Artist=artist).delete()
        return jsonify(message="OK")
    except:
        logger.exception("Error Deleting Artist Releases")
        return jsonify(message="ERROR")


@app.route('/release/delete/<release_id>/<delete_files>', methods=['POST'])
@login_required
def deleteRelease(release_id, delete_files):
    release = getRelease(release_id)
    if not release:
        return jsonify(message="ERROR")
    try:
        # TODO
        # if delete_files == "true":
        #     try:
        #         for track in release.Tracks:
        #             trackPath = track.Track.FilePath
        #             trackFilename = os.path.join(track.Track.FilePath, track.Track.FileName)
        #             os.remove(trackFilename)
        #             # if the folder is empty then delete the folder as well
        #             if trackPath:
        #                 if not os.listdir(trackPath):
        #                     os.rmdir(trackPath)
        #     except OSError:
        #         pass
        dbSession.delete(release)
        return jsonify(message="OK")
    except:
        logger.exception("Error Deleting Release")
        return jsonify(message="ERROR")


@app.route("/user/track/setrating/<release_id>/<track_id>/<rating>", methods=['POST'])
@login_required
def setUserTrackRating(release_id, track_id, rating):
    try:
        track = getTrack(track_id)
        user = getUser()
        if not track or not user:
            return jsonify(message="ERROR")
        now = arrow.utcnow().datetime
        userTrack = dbSession.query(UserTrack) \
                .filter(UserTrack.userId == user.id) \
                .filter(UserTrack.trackId == track.id).first()
        if not userTrack:
            userTrack = UserTrack()
            userTrack.roadieId = str(uuid.uuid4())
            userTrack.userId = user.id
            userTrack.trackId = track.id
            userTrack.playedCount = 0
            userTrack.rating = 0
            dbSession.add(userTrack)
        userTrack.rating = rating
        userTrack.lastPlayed = now
        dbSession.commit()
        trackAverage = dbSession.query(func.avg(UserTrack.rating)).filter(UserTrack.trackId == track.id).scalar()
        track.rating = trackAverage
        track.lastUpdated = now
        dbSession.commit()
        return jsonify(message="OK", average=trackAverage)
    except:
        logger.exception("Error Setting Track Rating")
        return jsonify(message="ERROR")


@app.route('/releasetrack/delete/<release_id>/<release_track_id>/<flag>', methods=['POST'])
@login_required
def deleteReleaseTrack(release_id, release_track_id, flag):
    try:
        # TODO
        # release = getRelease(release_id)
        # if not release:
        #     return jsonify(message="ERROR")
        # rts = []
        # for track in release.Tracks:
        #     if track.Track.id != objectid.ObjectId(release_track_id):
        #         rts.append(track)
        # release.Tracks = rts
        # session.commit()
        #
        # trackPath = None
        # trackFilename = None
        # if flag == 't' or flag == "f":
        #     # Delete the track
        #     track = Track.objects(id=release_track_id).first()
        #     if track:
        #         trackPath = track.FilePath
        #         trackFilename = os.path.join(track.FilePath, track.FileName)
        #         Track.delete(track)
        #
        # if flag == "f":
        #     # Delete the file
        #     try:
        #         if trackFilename:
        #             os.remove(trackFilename)
        #         # if the folder is empty then delete the folder as well
        #         if trackPath:
        #             if not os.listdir(trackPath):
        #                 os.rmdir(trackPath)
        #     except OSError:
        #         pass

        return jsonify(message="OK")
    except:
        logger.exception("Error Deleting Releae Track")
        return jsonify(message="ERROR")


@app.route('/artist/setimage/<artist_id>/<image_id>', methods=['POST'])
@login_required
def setArtistImage(artist_id, image_id):
    artist = getArtist(artist_id)
    if not artist:
        return jsonify(message="ERROR")
    image = dbSession.query(Image).filter(Image.roadieId == image_id).first()
    if image:
        img = PILImage.open(io.BytesIO(image.image)).convert('RGB')
        img.thumbnail(thumbnailSize)
        b = io.BytesIO()
        img.save(b, "JPEG")
        artist.thumbnail = b.getvalue()
        artist.lastUpdated = arrow.utcnow().datetime
        dbSession.commit()
        return jsonify(message="OK")
    return jsonify(message="ERROR")


@app.route('/release/setimage/<release_id>/<image_id>', methods=['POST'])
@login_required
def setReleaseImage(release_id, image_id):
    release = getRelease(release_id)
    if not release:
        return jsonify(message="ERROR")

    try:
        image = dbSession.query(Image).filter(Image.roadieId == image_id).first()
        if image:
            img = PILImage.open(io.BytesIO(image.image)).convert('RGB')
            img.thumbnail(thumbnailSize)
            b = io.BytesIO()
            img.save(b, "JPEG")
            release.thumbnail = b.getvalue()
            release.lastUpdated = arrow.utcnow().datetime
            dbSession.commit()
            return jsonify(message="OK")
    except:
        logger.exception("Error Setting Release Image")
        return jsonify(message="ERROR")


@app.route('/release/<roadieId>')
@login_required
def release(roadieId):
    release = getRelease(roadieId)
    if not release:
        return render_template('404.html'), 404
    releaseSummaries = conn.execute(text(
        "SELECT count(1) as trackCount, "
        "max(rm.releaseMediaNumber) as releaseMediaCount, "
        "sum(t.duration) as releaseTrackTime, "
        "sum(t.fileSize) as releaseTrackFileSize "
        "FROM track t "
        "join releasemedia rm on t.releaseMediaId = rm.id "
        "join release r on rm.releaseId = r.id "
        "where r.roadieId = '" + roadieId + "'", autocommit=True)
                                    .columns(trackCount=Integer, releaseMediaCount=Integer, releaseTrackTime=Integer,
                                             releaseTrackFileSize=Integer)) \
        .fetchone()
    return render_template('release.html',
                           release=release,
                           collectionReleases=release.collections,
                           userRelease=release.userRatings, trackCount=releaseSummaries[0],
                           releaseMediaCount=releaseSummaries[1] or 0,
                           releaseTrackTime=formatTimeMillisecondsNoDays(releaseSummaries[2]) or "0",
                           releaseTrackFileSize=sizeof_fmt(releaseSummaries[3]))


@app.route("/artist/play/<artist_id>/<doShuffle>")
@login_required
def playArtist(artist_id, doShuffle):
    artist = getArtist(artist_id)
    if not artist:
        return render_template('404.html'), 404
    tracks = []
    user = getUser()
    for release in artist.releases:
        for media in release.media:
            for track in sorted(media.tracks, key=lambda track: (media.releaseMediaNumber, track.trackNumber)):
                tracks.append(M3U.makeTrackInfo(user, release, track))
    if doShuffle == "1":
        random.shuffle(tracks)
    if user.doUseHtmlPlayer:
        session['tracks'] = tracks
        return player()
    return send_file(M3U.generate(tracks),
                     as_attachment=True,
                     attachment_filename="playlist.m3u")


@app.route("/release/play/<release_id>")
@login_required
def playRelease(release_id):
    release = getRelease(release_id)
    if not release:
        return render_template('404.html'), 404
    tracks = []
    user = getUser()
    for media in release.media:
        for track in media.tracks:
            tracks.append(M3U.makeTrackInfo(user, release, track))
    if user.doUseHtmlPlayer:
        session['tracks'] = tracks
        return player()
    return send_file(M3U.generate(tracks),
                     as_attachment=True,
                     attachment_filename="playlist.m3u")


@app.route("/track/play/<release_id>/<track_id>")
@login_required
def playTrack(release_id, track_id):
    release = getRelease(release_id)
    track = getTrack(track_id)
    if not release or not track:
        return render_template('404.html'), 404
    tracks = []
    user = getUser()
    tracks.append(M3U.makeTrackInfo(user, release, track))
    if user.doUseHtmlPlayer:
        session['tracks'] = tracks
        return player()
    return send_file(M3U.generate(tracks),
                     as_attachment=True,
                     attachment_filename="playlist.m3u")


@app.route("/que/play", methods=['POST'])
@login_required
def playQue():
    user = getUser()
    tracks = []
    for t in request.json:
        if (t["type"] == "track"):
            release = getRelease(t["releaseId"])
            track = getTrack(t["trackId"])
            if release and track:
                tracks.append(M3U.makeTrackInfo(user, release, track))
    if user.doUseHtmlPlayer:
        session['tracks'] = tracks
        return player()
    return send_file(M3U.generate(tracks),
                     as_attachment=True,
                     attachment_filename="playlist.m3u")


@app.route("/que/save/<que_name>", methods=['POST'])
@login_required
def saveQue(que_name):
    if not que_name or not current_user:
        return jsonify(message="ERROR")
    tracks = []
    for t in request.json:
        if (t["type"] == "track"):
            track = getTrack(t["id"])
            if track:
                tracks.append(track)
    user = getUser()
    pl = dbSession.query(Playlist).filter(Playlist.userId == user.id).filter(Playlist.name == que_name).first()
    if not pl:
        # adding a new playlist
        pl = Playlist()
        pl.userId == user.id
        pl.name = que_name
        pl.tracks = tracks
        dbSession.add(pl)
        dbSession.commit()
    else:
        # adding tracks to an existing playlist
        if pl.Tracks:
            for plt in pl.Tracks:
                if plt not in tracks:
                    tracks.append(plt)
        else:
            pl.Tracks = tracks
        dbSession.commit()
    return jsonify(message="OK")


@app.route("/stream/track/<user_id>/<track_id>")
def streamTrack(user_id, track_id):
    if track_id.endswith(".mp3"):
        track_id = track_id[:-4]
    track = getTrack(track_id)
    if not track:
        return render_template('404.html'), 404
    track.playedCount += 1
    dbSession.commit()
    now = arrow.utcnow().datetime
    track.lastPlayed = now
    dbSession.commit()
    mp3File = pathToTrack(track)
    if not os.path.isfile(mp3File):
        logger.debug("! Unable To Find Track File [" + mp3File + "]")
        return render_template('404.html'), 404
    (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(mp3File)
    headers = Headers()
    headers.add('Content-Disposition', 'attachment', filename=track.fileName)
    headers.add('Content-Transfer-Encoding', 'binary')
    status = 200
    size = size
    begin = 0
    end = size - 1
    cachetimeout = 86400  # 24 hours
    if request.headers.has_key("Range"):
        status = 206
        headers.add('Accept-Ranges', 'bytes')
        ranges = findall(r"\d+", request.headers["Range"])
        begin = int(ranges[0])
        if len(ranges) > 1:
            end = int(ranges[1])
        headers.add('Content-Range', 'bytes %s-%s/%s' % (str(begin), str(end), str((end - begin) + 1)))
    headers.add('Content-Length', str((end - begin) + 1))
    isFullRequest = begin == 0 and (end == (size - 1))
    isEndRangeRequest = begin > 0 and (end != (size - 1))
    # user = None;
    if isFullRequest or isEndRangeRequest and current_user:
        user = getUser(user_id)
        if user:
            userRating = dbSession.query(UserTrack) \
                .filter(UserTrack.userId == user.id) \
                .filter(UserTrack.trackId == track.id).first()
            if not userRating:
                userRating = UserTrack()
                userRating.roadieId = str(uuid.uuid4())
                userRating.userId = user.id
                userRating.trackId = track.id
                userRating.playedCount = 0
                userRating.rating = 0
            userRating.playedCount += 1
            userRating.lastPlayed = now
            dbSession.add(userRating)
            dbSession.commit()
            try:
                if clients:
                    data = json.dumps({'message': "OK",
                                       'lastPlayedInfo': {
                                           'TrackId': str(track.roadieId),
                                           'TrackTitle': track.title,
                                           'ReleaseId': str(track.releasemedia.release.roadieId),
                                           'ReleaseTitle': track.releasemedia.release.title,
                                           'ReleaseThumbnail': "/images/release/thumbnail/" + str(
                                               track.releasemedia.release.roadieId),
                                           'ArtistId': str(track.releasemedia.release.artist.roadieId),
                                           'ArtistName': track.releasemedia.release.artist.name,
                                           'ArtistThumbnail': "/images/artist/thumbnail/" + str(
                                               track.releasemedia.release.artist.roadieId),
                                           'UserId': str(user.roadieId),
                                           'Username': user.username,
                                           'UserThumbnail': "/images/user/avatar/" + str(user.roadieId),
                                           'UserRating': userRating.rating,
                                           'LastPlayed': arrow.get(now).humanize()
                                       }})

                    for client in clients:
                        client.write_message(data)
            except:
                pass
    data = None
    with open(mp3File, 'rb') as f:
        f.seek(begin)
        data = f.read((end - begin) + 1)
    response = Response(data, status=status, mimetype="audio/mpeg", headers=headers, direct_passthrough=True)
    response.cache_control.public = True
    response.cache_control.max_age = cachetimeout
    response.last_modified = int(ctime)
    response.expires = int(time()) + cachetimeout
    response.set_etag('%s%s' % (track.id, ctime))
    response.make_conditional(request)
    logger.debug(
        "Streaming To Ip [" + request.remote_addr + "] Mp3 [" + mp3File + "], Size [" + str(size) + "], Begin [" + str(
            begin) + "] End [" + str(end) + "]")
    return response


@app.route('/stats')
@login_required
@nocache
def stats():
    counts = {'artists': "{0:,}".format(Artist.objects().count()),
              'labels': "{0:,}".format(Label.objects().count()),
              'releases': "{0:,}".format(Release.objects().count()),
              'tracks': "{0:,}".format(Track.objects().count())
              }

    totalTime = Track.objects().aggregate(
        {"$group": {"_id": "null", "total": {"$sum": "$Length"}}},
    )
    for t in totalTime:
        counts['length'] = t['total']

    top10ArtistsByReleases = Release.objects().aggregate(
        {"$group": {"_id": "$Artist", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    )
    top10Artists = {}
    for a in top10ArtistsByReleases:
        artist = Artist.objects(id=a['_id']).first()
        top10Artists[artist] = str(a['count']).zfill(3)

    top10ArtistsByTracks = Track.objects().aggregate(
        {"$group": {"_id": "$Artist", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    )
    top10ArtistsTracks = {}
    for a in top10ArtistsByTracks:
        artist = Artist.objects(id=a['_id']).first()
        top10ArtistsTracks[artist] = str(a['count']).zfill(4)

    topRatedReleases = Release.objects().order_by('-Rating', 'FilePath', 'Title')[:10]

    topRatedTracks = Track.objects(Rating__gt=0).order_by('-Rating', 'FilePath', 'Title')[:25]

    mostRecentReleases = Release.objects().order_by('-CreatedDate', 'FilePath', 'Title')[:25]

    return render_template('stats.html', top10Artists=sorted(top10Artists.items(), key=itemgetter(1), reverse=True)
                           , top10ArtistsByTracks=sorted(top10ArtistsTracks.items(), key=itemgetter(1), reverse=True)
                           , topRatedReleases=topRatedReleases
                           , topRatedTracks=topRatedTracks
                           , mostRecentReleases=mostRecentReleases
                           , counts=counts)


@app.route("/stats/play/<option>")
@login_required
def playStats(option):
    user = User.objects(id=current_user.id).first()
    tracks = []
    if option == "top25songs":
        for track in Track.objects(Rating__gt=0).order_by('-Rating', 'FilePath', 'Title')[:25]:
            release = Release.objects(Tracks__Track=track).first()
            tracks.append(M3U.makeTrackInfo(user, release, track))
        if user.doUseHtmlPlayer:
            session['tracks'] = tracks
            return player()
        return send_file(M3U.generate(tracks),
                         as_attachment=True,
                         attachment_filename="playlist.m3u")
    if option == "top10Albums":
        for release in Release.objects().order_by('-Rating', 'FilePath', 'Title')[:10]:
            user = User.objects(id=current_user.id).first()
            for track in sorted(release.Tracks, key=lambda track: (track.ReleaseMediaNumber, track.TrackNumber)):
                tracks.append(M3U.makeTrackInfo(user, release, track.Track))
        if user.doUseHtmlPlayer:
            session['tracks'] = tracks
            return player()
        return send_file(M3U.generate(tracks),
                         as_attachment=True,
                         attachment_filename="playlist.m3u")


def makeImageResponse(imageBytes, lastUpdated, imageName, etag, mimetype='image/jpg'):
    rv = send_file(io.BytesIO(imageBytes),
                   attachment_filename=imageName,
                   conditional=True,
                   mimetype=mimetype)
    rv.last_modified = lastUpdated
    rv.make_conditional(request)
    rv.set_etag(etag)
    return rv


def getAndReturnImage(imageId, height, width, notFoundReplacement):
    try:
        releaseImage = dbSession.query(Image).filter(Image.roadieId == imageId).first()
        if releaseImage:
            h = int(height)
            w = int(width)
            img = PILImage.open(io.BytesIO(releaseImage.image)).convert('RGB')
            size = h, w
            img.thumbnail(size)
            b = io.BytesIO()
            img.save(b, "JPEG")
            ba = b.getvalue()
            etag = hashlib.sha1(
                ('%s%s' % (releaseImage.roadieId, releaseImage.lastUpdated)).encode('utf-8')).hexdigest()
            return makeImageResponse(ba, releaseImage.lastUpdated, releaseImage.roadieId, etag)
    except:
        logger.exception("getAndReturnImage [" + str(imageId) + "]")
        pass
    return send_file(notFoundReplacement)


@app.route("/images/release/<image_id>/<height>/<width>")
def getReleaseImage(image_id, height, width):
    return getAndReturnImage(image_id, height, width, "static/img/release.gif")


@app.route('/images/artist/<image_id>/<height>/<width>')
def getArtistImage(image_id, height, width):
    return getAndReturnImage(image_id, height, width, "static/img/artist.gif")


@app.route("/images/collection/thumbnail/<collection_id>")
def getCollectionThumbnailImage(collection_id):
    collection = dbSession.query(Collection).filter(Collection.roadieId == collection_id).first()
    try:
        if collection:
            etag = hashlib.sha1(('%s%s' % (collection.id, collection.LastUpdated)).encode('utf-8')).hexdigest()
            return makeImageResponse(collection.thumbnail, collection.lastUpdated,
                                     "a_tn_" + str(collection.id) + ".jpg", etag)
    except:
        return send_file("static/img/collection.gif")


@app.route("/images/artist/thumbnail/<artistId>")
def getArtistThumbnailImage(artistId):
    artist = getArtist(artistId)
    try:
        if artist:
            etag = hashlib.sha1(('%s%s' % (artist.roadieId, artist.lastUpdated)).encode('utf-8')).hexdigest()
            return makeImageResponse(artist.thumbnail, artist.lastUpdated, "a_tn_" + str(artist.roadieId) + ".jpg",
                                     etag)

    except:
        return send_file("static/img/artist.gif")


@app.route("/images/release/thumbnail/<roadieId>")
def getReleaseThumbnailImage(roadieId):
    release = getRelease(roadieId)
    try:
        if not release or not release.thumbnail:
            return send_file("static/img/release.gif")
        if release:
            etag = hashlib.sha1(('%s%s' % (release.id, release.lastUpdated)).encode('utf-8')).hexdigest()
            return makeImageResponse(release.thumbnail, release.lastUpdated, "r_tn_" + str(release.roadieId) + ".jpg",
                                     etag)
    except:
        return send_file("static/img/release.gif")


def jdefault(o):
    if isinstance(o, set):
        return list(o)
    return o.__dict__


@app.route("/images/find/<type>/<type_id>", methods=['POST'])
def findImageForType(type, type_id):
    if type == 'r':  # release
        release = getRelease(type_id)
        if not release:
            return jsonify(message="ERROR")
        data = []
        searcher = ImageSearcher()
        query = release.title
        if 'query' in request.form:
            query = request.form['query']
        referer = request.url_root
        gs = searcher.googleSearchImages(referer, request.remote_addr, query)
        if gs:
            for g in gs:
                data.append(g)
        it = searcher.itunesSearchArtistAlbumImages(referer, release.artist.name, release.title)
        if it:
            for i in it:
                data.append(i)
        return Response(json.dumps({'message': "OK", 'query': query, 'data': data}, default=jdefault),
                        mimetype="application/json")
    elif type == 'a':  # artist
        return jsonify(message="ERROR")
    else:
        return jsonify(message="ERROR")


@app.route("/release/setCoverViaUrl/<release_id>", methods=['POST'])
def setCoverViaUrl(release_id):
    try:
        release = getRelease(release_id)
        if not release:
            return jsonify(message="ERROR")
        url = request.form['url']
        searcher = ImageSearcher()
        imageBytes = searcher.getImageBytesForUrl(url)
        if imageBytes:
            img = PILImage.open(io.BytesIO(imageBytes)).convert('RGB')
            img.thumbnail(thumbnailSize)
            b = io.BytesIO()
            img.save(b, "JPEG")
            release.thumbnail = b.getvalue()
            release.lastUpdated = arrow.utcnow().datetime
            dbSession.commit()
        return jsonify(message="OK")
    except:
        logger.exception("Error Setting Release Image via Url")
        return jsonify(message="ERROR")


api.add_resource(ArtistListApi, '/api/v1.0/artists')
api.add_resource(ReleaseListApi, '/api/v1.0/releases')
api.add_resource(TrackListApi, '/api/v1.0/tracks')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(id):
    return getUser(id)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    pwd = bcrypt.generate_password_hash(request.form['password'])
    user = User()
    user.username = request.form['username']
    user.password = pwd
    user.email = request.form['email']
    user.registeredOn = arrow.utcnow().datetime
    user.roadieId = str(uuid.uuid4())
    dbSession.add(user)
    dbSession.commit()
    if user.id == 1:
        # First user set them up as admin
        adminRole = dbSession.query(UserRole).filter(UserRole.name == "Admin").first()
        if not adminRole:
            adminRole = UserRole()
            adminRole.roadieId = str(uuid.uuid4())
            adminRole.name = "Admin"
            adminRole.description = "Users with Administrative (full) access"
            adminRole.status = 1
            dbSession.add(adminRole)
        user.roles = []
        user.roles.append(adminRole)
        dbSession.commit()
    flash('User successfully registered')
    return redirect(url_for('login'))


@app.route("/profile/edit", methods=['GET', 'POST'])
def editProfile():
    user = getUser()
    if not user:
        return render_template('404.html'), 404
    if request.method == 'GET':
        return render_template('profileEdit.html', user=user)
    doUseHTMLPlayerSet = False
    if 'useHTMLPlayer' in request.form:
        doUseHTMLPlayerSet = True
    encryptedPassword = None
    password = request.form['password']
    if password:
        encryptedPassword = bcrypt.generate_password_hash(password)
    email = request.form['email']
    userWithDuplicateEmail = dbSession.query(User).filter(User.email == email, User.id != user.id).first()
    if userWithDuplicateEmail:
        flash('Email Address Already Exists!', 'error')
        return redirect(url_for('profile/edit'))
    file = request.files['avatar'];
    if file:
        img = PILImage.open(io.BytesIO(file.stream.read()))
        img.thumbnail(thumbnailSize)
        b = io.BytesIO()
        img.save(b, "PNG")
        user.avatar = b.getvalue()

    if encryptedPassword:
        user.password = encryptedPassword
    user.email = email
    user.doUseHTMLPlayer = doUseHTMLPlayerSet
    user.lastUpdated = arrow.utcnow().datetime
    if user.id in userCache:
        userCache[user.id] = user
    dbSession.commit()
    flash('Profile Edited successfully')
    return redirect(url_for("index"))


@app.route("/images/user/avatar/<user_id>")
def getUserAvatarThumbnailImage(user_id):
    user = getUser(user_id)
    try:
        if user:
            if not user.avatar:
                return send_file("static/img/user.png")
            etag = hashlib.sha1(str(user.lastUpdated).encode('utf-8')).hexdigest()
            return makeImageResponse(user.avatar, user.lastUpdated, 'avatar.png', etag, "image/png")
    except:
        return send_file("static/img/user.png")


@app.route('/login', methods=['GET', 'POST'])
def login():
    next = get_redirect_target()
    if request.method == 'GET':
        return render_template('login.html', next=next)
    username = request.form['username']
    password = request.form['password']
    remember_me = False
    if 'remember_me' in request.form:
        remember_me = True
    registered_user = dbSession.query(User).filter(User.username == username).first()
    if registered_user and bcrypt.check_password_hash(registered_user.password, password):
        registered_user.LastLogin = arrow.utcnow().datetime
        dbSession.commit()
        login_user(registered_user, remember=remember_me)
        flash('Logged in successfully')
        return redirect_back('index')
    else:
        flash('Username or Password is invalid', 'error')
        return redirect(url_for('login'))


def public_endpoint(function):
    function.is_public = True
    return function


@app.route('/scanStorage')
def scanStorage():
    return render_template('scanStorage.html')


@app.route('/playlists')
@login_required
def playlists():
    user = getUser()
    userPlaylists = Playlist.objects(User=user).order_by("Name").all()
    #  sharedPlaylists =  Playlist.objects(User__ne = user).all() #.order_by('User__Name', 'Name').all()
    return render_template('playlist.html', userPlaylists=userPlaylists)  # , sharedPlaylists=sharedPlaylists)


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc


def get_redirect_target():
    for target in request.values.get('next'), request.referrer:
        if not target:
            continue
        if is_safe_url(target):
            return target


def redirect_back(endpoint, **values):
    target = request.form['next']
    if not target or not is_safe_url(target):
        target = url_for(endpoint, **values)
    return redirect(target)


@app.route("/collections")
@login_required
def collections():
    collections = []
    for collection in Collection.objects().order_by("Name"):
        collections.append({
            'id': collection.id,
            'Name': collection.Name,
            'ReleaseCount': 0  # collection.Releases # This is crazy slow
        })
    notFoundEntryInfos = []
    if 'notFoundEntryInfos' in dbSession:
        notFoundEntryInfos = dbSession['notFoundEntryInfos']
        session['notFoundEntryInfos'] = None
    return render_template('collections.html', collections=collections, notFoundEntryInfos=notFoundEntryInfos)


@app.route('/collection/<collection_id>')
@login_required
def collection(collection_id):
    collection = Collection.objects(id=collection_id).first()
    if not collection:
        return render_template('404.html'), 404
    tracks = 0
    sumTime = 0
    counts = {'releases': "0",
              'tracks': "0",
              'length': 0}
    for release in collection.Releases:
        try:
            tracks += len(release.Release.Tracks)
            for track in release.Release.Tracks:
                sumTime += track.Track.Length
            counts = {'releases': "{0:,}".format(len(collection.Releases)),
                      'tracks': "{0:,}".format(tracks),
                      'length': sumTime}
        except:
            pass
    notFoundEntryInfos = []
    if 'notFoundEntryInfos' in dbSession:
        notFoundEntryInfos = dbSession['notFoundEntryInfos']
        session['notFoundEntryInfos'] = None
    return render_template('collection.html', collection=collection, counts=counts,
                           notFoundEntryInfos=notFoundEntryInfos)


@app.route("/collection/play/<collection_id>")
@login_required
def playCollection(collection_id):
    collection = Collection.objects(id=collection_id).first()
    if not collection:
        return render_template('404.html'), 404
    user = getUser()
    tracks = []
    for release in collection.Releases:
        for track in sorted(release.Release.Tracks, key=lambda track: (track.ReleaseMediaNumber, track.TrackNumber)):
            tracks.append(M3U.makeTrackInfo(user, release.Release, track.Track))
    if user.DoUseHTMLPlayer:
        session['tracks'] = tracks
        return player()
    return send_file(M3U.generate(tracks),
                     as_attachment=True,
                     attachment_filename=collection.Name + ".m3u")


@app.route("/collections/updateall", methods=['POST'])
def updateAllCollections():
    try:
        notFoundEntryInfos = []
        for collection in Collection.objects(ListInCSVFormat__ne=None, ListInCSV__ne=None):
            i = CollectionImporter(collection.id, False, collection.ListInCSVFormat, None)
            i.importCsvData(io.StringIO(collection.ListInCSV))
            for i in i.notFoundEntryInfo:
                notFoundEntryInfos.append(i)
            session['notFoundEntryInfos'] = notFoundEntryInfos
        return jsonify(message="OK")
    except:
        logger.exception("Error Updating Collection")
        return jsonify(message="ERROR")


@app.route("/collection/update/<collection_id>", methods=['POST'])
def updateCollection(collection_id):
    try:
        notFoundEntryInfos = []
        collection = Collection.objects(id=collection_id).first()
        if not collection or not collection.ListInCSVFormat or not collection.ListInCSV:
            return jsonify(message="ERROR")
        i = CollectionImporter(collection.id, False, collection.ListInCSVFormat, None)
        i.importCsvData(io.StringIO(collection.ListInCSV))
        for i in i.notFoundEntryInfo:
            notFoundEntryInfos.append(i)
        session['notFoundEntryInfos'] = notFoundEntryInfos
        return jsonify(message="OK")
    except:
        logger.exception("Error Updating Collection")
        return jsonify(message="ERROR")


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route("/singletrackreleasefinder", defaults={'count': 100})
@app.route("/singletrackreleasefinder/<count>")
@login_required
def singletrackreleasefinder(count):
    count = int(count)
    singleTrackReleases = Release.objects(__raw__={'Tracks': {'$size': 1}}).order_by('Title', 'Artist.Name')
    return render_template('singletrackreleasefinder.html', total=singleTrackReleases.count(),
                           singleTrackReleases=singleTrackReleases[:count])


@app.route('/dupfinder')
@login_required
def dupFinder():
    artists = []
    for a in Artist.objects():
        artists.append({
            'id': a.id,
            'Name': a.Name,
            'SortName': a.SortName
        })

    duplicateArtists = []
    for artist in artists:
        doContinue = True
        for da in duplicateArtists:
            if artist['id'] == da['a']['id']:
                doContinue = False
                continue
        if doContinue:
            for a in artists:
                aName = a['Name'].lower().strip()
                aSortname = None
                sn = a['SortName']
                if sn:
                    aSortname = sn.lower().strip()
                artistName = artist['Name'].lower().strip()
                artistSortName = None
                sn = artist['SortName']
                if sn:
                    artistSortName = sn.lower().strip()
                if (artistName == aName or
                        (aSortname and artistSortName and artistSortName == aSortname) or (
                            artistSortName and artistSortName == aName)) and artist['id'] != a['id']:
                    duplicateArtists.append({
                        'artist': artist,
                        'a': a
                    })

    return render_template('dupfinder.html', duplicateArtists=duplicateArtists)


@app.route('/artist/merge/<merge_into_id>/<merge_id>', methods=['POST'])
@login_required
def mergeArtists(merge_into_id, merge_id):
    try:
        artist = Artist.objects(id=merge_into_id).first()
        artistToMerge = Artist.objects(id=merge_id).first()
        if not artist or not artistToMerge:
            return jsonify(message="ERROR")
        now = arrow.utcnow().datetime
        Track.objects(Artist=artistToMerge).update(Artist=artist)
        Release.objects(Artist=artistToMerge).update(Artist=artist)
        UserArtist.objects(Artist=artistToMerge).update(Artist=artist)
        for altName in artistToMerge.AlternateNames:
            if not altName in artist.AlternateNames:
                artist.AlternateNames.append(altName)
        for associated in artistToMerge.AssociatedArtists:
            if not associated in artist.AssociatedArtists:
                artist.AssociatedArtists.append(associated)
        artist.BirthDate = artist.BirthDate or artistToMerge.BirthDate
        artist.BeginDate = artist.BeginDate or artistToMerge.BeginDate
        artist.EndDate = artist.EndDate or artistToMerge.EndDate
        for image in artistToMerge.Images:
            artist.Images.append(image)
        artist.Profile = artist.Profile or artistToMerge.Profile
        artist.MusicBrainzId = artist.MusicBrainzId or artistToMerge.MusicBrainzId
        artist.RealName = artist.RealName or artistToMerge.RealName
        artist.Thumbnail = artist.Thumbnail or artistToMerge.Thumbnail
        artist.Rating = artist.Rating or artistToMerge.Rating
        for tag in artistToMerge.Tags:
            if not tag in artist.Tags:
                artist.Tags.append(tag)
        for url in artistToMerge.Urls:
            if not url in artist.Urls:
                artist.Urls.append(url)
        Artist.save(artist)
        Artist.delete(artistToMerge)
        return jsonify(message="OK")

    except:
        logger.exception("Error Merging Artists")
        return jsonify(message="ERROR")


@app.route("/player")
@login_required
def player():
    tracks = session['tracks']
    return render_template('player.html', tracks=tracks)


class WebSocket(WebSocketHandler):
    # def data_received(self, chunk):
    #     pass
    #
    # def on_message(self, message):
    #     pass

    def open(self, *args):
        clients.append(self)

    def on_close(self):
        clients.remove(self)


if __name__ == '__main__':
    admin = admin.Admin(app, 'Roadie: Admin', template_mode='bootstrap3')
    admin.add_view(RoadieArtistModelView(Artist, dbSession))
    admin.add_view(RoadieCollectionModelView(Collection, dbSession))
    admin.add_view(RoadieModelView(Label, dbSession))
    admin.add_view(RoadiePlaylistModelView(Playlist, dbSession))
    admin.add_view(RoadieReleaseModelView(Release, dbSession))
    # admin.add_view(RoadieTrackModelView(Track, session))
    admin.add_view(RoadieModelAdminRequiredView(User, category='User', session=dbSession))
    admin.add_view(RoadieUserArtistModelView(UserArtist, category='User', session=dbSession))
    admin.add_view(RoadieUserReleaseModelView(UserRelease, category='User', session=dbSession))
    admin.add_view(RoadieUserTrackModelView(UserTrack, category='User', session=dbSession))
    admin.add_view(RoadieModelView(Genre, category='Reference Fields', session=dbSession))
    admin.add_view(RoadieModelAdminRequiredView(UserRole, category='Reference Fields', session=dbSession))
    container = WSGIContainer(app)
    server = Application([
        (r'/websocket/', WebSocket),
        (r'.*', FallbackHandler, dict(fallback=container))
    ])
    server.listen(5000)
    IOLoop.instance().start()
