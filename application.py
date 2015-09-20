import io
import os
import hashlib
import json
import random
import zipfile
import zlib
from itertools import groupby
from time import time
from operator import itemgetter
from re import findall
from urllib.parse import urlparse, urljoin

import arrow
from bson import objectid
from PIL import Image
from flask import Flask, jsonify, render_template, send_file, Response, request, session, \
    flash, url_for, redirect, g
import flask_admin as admin
from flask_restful import Api
from flask_mongoengine import MongoEngine
from mongoengine import Q
from tornado.wsgi import WSGIContainer
from tornado.web import Application, FallbackHandler
from tornado.websocket import WebSocketHandler
from tornado.ioloop import IOLoop

from werkzeug.datastructures import Headers

from importers.collectionImporter import CollectionImporter
from resources.artistApi import ArtistApi
from resources.artistListApi import ArtistListApi
from resources.imageSearcher import ImageSearcher, ImageSearchResult
from resources.releaseListApi import ReleaseListApi
from resources.trackListApi import TrackListApi
from resources.processor import Processor
from resources.logger import Logger
from resources.id3 import ID3
from resources.models import Artist, ArtistType, Collection, Genre, Label, \
    Playlist, Quality, Release, Track, User, UserArtist, UserRelease, UserRole, UserTrack
from resources.m3u import M3U
from flask.ext.mongoengine import MongoEngine, MongoEngineSessionInterface
from flask.ext.login import LoginManager, login_user, logout_user, \
    current_user, login_required
from flask.ext.bcrypt import Bcrypt
from resources.nocache import nocache
from resources.jinjaFilters import format_tracktime, format_timedelta, calculate_release_tracks_Length, \
    group_release_tracks_filepaths, format_age_from_date, calculate_release_discs, count_new_lines
from resources.validator import Validator
from viewModels.RoadieModelView import RoadieModelView, RoadieModelAdminRequiredView
from viewModels.RoadieReleaseModelView import RoadieReleaseModelView
from viewModels.RoadieTrackModelView import RoadieTrackModelView
from viewModels.RoadieCollectionModelView import RoadieCollectionModelView
from viewModels.RoadieUserModelView import RoadieUserModelView
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

db = MongoEngine(app)
app.session_interface = MongoEngineSessionInterface(db)
flask_bcrypt = Bcrypt(app)
bcrypt = Bcrypt()
api = Api(app)

logger = Logger()


@app.before_request
def before_request():
    g.siteName = siteName
    g.user = current_user


@app.route('/')
@login_required
def index():
    lastPlayedInfos = []
    for ut in UserTrack.objects().order_by('-LastPlayed')[:35]:
        info = {
            'TrackId': str(ut.Track.id),
            'TrackTitle': ut.Track.Title,
            'ReleaseId': str(ut.Release.id),
            'ReleaseTitle': ut.Release.Title,
            'ReleaseThumbnail': "/images/release/thumbnail/" + str(ut.Release.id),
            'ArtistId': str(ut.Track.Artist.id),
            'ArtistName': ut.Track.Artist.Name,
            'ArtistThumbnail': "/images/artist/thumbnail/" + str(ut.Track.Artist.id),
            'UserId': str(ut.User.id),
            'Username': ut.User.Username,
            'UserThumbnail': "/images/user/avatar/" + str(ut.User.id),
            'UserRating': ut.Rating,
            'LastPlayed': arrow.get(ut.LastPlayed).humanize()
        }
        lastPlayedInfos.append(info)
    wsRoot = request.url_root.replace("http://", "ws://")
    randomSeed1 = random.randint(1, 1000000)
    randomSeed2 = random.randint(randomSeed1, 1000000)
    releases = []
    for release in Release.objects(Q(Random__gte=randomSeed1) & Q(Random__lte=randomSeed2)).order_by('Random')[:12]:
        releases.append({
            'id': release.id,
            'ArtistName': release.Artist.Name,
            'Title': release.Title,
            'UserRating': 0
        })
    return render_template('home.html', lastPlayedInfos=lastPlayedInfos, wsRoot=wsRoot, releases=releases)


@app.route("/release/setTitle/<release_id>/<new_title>/<set_tracks_title>/<create_alternate_name>", methods=['POST'])
def setReleaseTitle(release_id, new_title, set_tracks_title, create_alternate_name):
    release = Release.objects(id = release_id).first()
    user = User.objects(id=current_user.id).first()
    now = arrow.utcnow().datetime
    if not release or not user or not new_title:
        return jsonify(message="ERROR")
    oldTitle = release.Title
    release.Title = new_title
    release.LastUpdated = now
    if create_alternate_name == "true" and not new_title in release.AlternateNames:
            release.AlternateNames.append(oldTitle)
    Release.save(release)
    if set_tracks_title == "true":
        for track in release.Tracks:
            trackPath = os.path.join(track.Track.FilePath, track.Track.FileName)
            id3 = ID3(trackPath, config)
            id3.updateFromRelease(release, track)
    return jsonify(message="OK")


@app.route("/release/random/<count>", methods=['POST'])
def randomRelease(count):
    try:
        randomSeed1 = random.randint(1, 1000000)
        randomSeed2 = random.randint(randomSeed1, 1000000)
        releases = []
        for release in Release.objects(Q(Random__gte=randomSeed1) & Q(Random__lte=randomSeed2)).order_by('Random')[
                       :int(count)]:
            releaseInfo = {
                'id': str(release.id),
                'ArtistName': release.Artist.Name,
                'Title': release.Title,
                'UserRating': 0
            }
            releases.append(releaseInfo)
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
    randomSeed1 = random.randint(1, 1000000)
    randomSeed2 = random.randint(randomSeed1, 1000000)
    user = User.objects(id=current_user.id).first()
    if type == "artist":
        artist = Artist.objects(Q(Random__gte=randomSeed1) & Q(Random__lte=randomSeed2)).order_by('Random').first()
        return playArtist(artist.id, "0")
    elif type == "release":
        release = Release.objects(Q(Random__gte=randomSeed1) & Q(Random__lte=randomSeed2)).order_by('Random').first()
        return playRelease(release.id)
    elif type == "tracks":
        tracks = []
        for track in Track.objects(Q(Random__gte=randomSeed1) & Q(Random__lte=randomSeed2)).order_by('Random')[:35]:
            release = Release.objects(Tracks__Track = track).first()
            t = M3U.makeTrackInfo(user, release, track)
            if t:
                tracks.append(t)
        if user.DoUseHTMLPlayer:
            session['tracks'] = tracks
            return player()
        return send_file(M3U.generate(tracks),
                         as_attachment=True,
                         attachment_filename="playlist.m3u")


@app.route('/db/reseed', methods=['POST'])
@login_required
def reseed():
    try:
        now = arrow.utcnow().datetime
        for artist in Artist.objects():
            try:
                artist.Random = random.randint(1, 1000000)
                artist.Last = now
                Artist.save(artist)
            except:
                logger.exception("Error In Reseeding Artist")
                pass
        logger.debug("Completed Reseeding Artists")
        for release in Release.objects():
            try:
                release.Random = random.randint(1, 1000000)
                release.Last = now
                Release.save(release)
            except:
                logger.exception("Error In Reseeding Release")
                pass
        logger.debug("Completed Reseeding Releases")
        for track in Track.objects():
            try:
                track.Random = random.randint(1, 1000000)
                track.Last = now
                Track.save(track)
            except:
                logger.exception("Error In Reseeding Track")
                pass
        logger.debug("Completed Reseeding Tracks")
        return jsonify(message="OK")
    except:
        logger.exception("Error In Reseeding Random")
        return jsonify(message="ERROR")



@app.route('/artist/<artist_id>')
@login_required
def artist(artist_id):
    artist = Artist.objects(id=artist_id).first()
    if not artist:
        return render_template('404.html'), 404
    releases = Release.objects(Artist=artist)
    counts = {'releases': "{0:,}".format(Release.objects(Artist=artist).count()),
              'tracks': "{0:,}".format(Track.objects(Artist=artist).count())}
    totalTime = Track.objects(Artist=artist).aggregate(
        {"$group": {"_id": "null", "total": {"$sum": "$Length"}}},
    )
    user = User.objects(id=current_user.id).first()
    userArtist = UserArtist.objects(User=user, Artist=artist).first()
    for t in totalTime:
        counts['length'] = t['total']
    return render_template('artist.html', artist=artist, releases=releases, counts=counts, userArtist=userArtist)


@app.route("/user/artist/setrating/<artist_id>/<rating>", methods=['POST'])
@login_required
def setUserArtistRating(artist_id, rating):
    try:
        artist = Artist.objects(id=artist_id).first()
        user = User.objects(id=current_user.id).first()
        if not artist or not user:
            return jsonify(message="ERROR")
        now = arrow.utcnow().datetime
        userArtist = UserArtist.objects(User=user, Artist=artist).first()
        if not userArtist:
            userArtist = UserArtist(User=user, Artist=artist)
        userArtist.Rating = rating
        userArtist.LastUpdated = now
        UserArtist.save(userArtist)
        # Update artist average rating
        artistAverage = UserArtist.objects(Artist=artist).aggregate_average('Rating')
        artist.Rating = artistAverage
        artist.LastUpdated = now
        Artist.save(artist)
        return jsonify(message="OK", average=artistAverage)
    except:
        logger.exception("Error Setting Artist Rating")
        return jsonify(message="ERROR")


@app.route("/user/artist/toggledislike/<artist_id>/<toggle>", methods=['POST'])
@login_required
def toggleUserArtistDislike(artist_id, toggle):
    try:
        artist = Artist.objects(id=artist_id).first()
        user = User.objects(id=current_user.id).first()
        if not artist or not user:
            return jsonify(message="ERROR")
        now = arrow.utcnow().datetime
        userArtist = UserArtist.objects(User=user, Artist=artist).first()
        if not userArtist:
            userArtist = UserArtist(User=user, Artist=artist)
        userArtist.IsDisliked = toggle.lower() == "true"
        userArtist.LastUpdated = now
        if userArtist.IsDisliked:
            userArtist.Rating = 0
        UserArtist.save(userArtist)
        artistAverage = UserArtist.objects(Artist=artist).aggregate_average('Rating')
        if userArtist.IsDisliked:
            # Update artist average rating
            artist.Rating = artistAverage
            artist.LastUpdated = now
            Artist.save(artist)
        return jsonify(message="OK", average=artistAverage)
    except:
        logger.exception("Error Setting Artist Dislike")
        return jsonify(message="ERROR")


@app.route("/user/artist/togglefavorite/<artist_id>/<toggle>", methods=['POST'])
@login_required
def toggleUserArtistFavorite(artist_id, toggle):
    try:
        artist = Artist.objects(id=artist_id).first()
        user = User.objects(id=current_user.id).first()
        if not artist or not user:
            return jsonify(message="ERROR")
        userArtist = UserArtist.objects(User=user, Artist=artist).first()
        if not userArtist:
            userArtist = UserArtist(User=user, Artist=artist)
        userArtist.IsFavorite = toggle.lower() == "true"
        userArtist.LastUpdated = arrow.utcnow().datetime
        UserArtist.save(userArtist)
        return jsonify(message="OK")
    except:
        logger.exception("Error Toggling Favorite")
        return jsonify(message="ERROR")


@app.route("/release/movetrackstocd/<release_id>/<selected_to_cd>", methods=['POST'])
@login_required
def movetrackstocd(release_id, selected_to_cd):
    release = Release.objects(id=release_id).first()
    user = User.objects(id=current_user.id).first()
    if not release or not user:
        return jsonify(message="ERROR")
    releaseMediaNumber = int(selected_to_cd)
    tracksToMove = request.form['tracksToMove']
    now = arrow.utcnow().datetime
    for trackToMove in tracksToMove.split(','):
        for track in release.Tracks:
            if str(track.Track.id) == trackToMove:
                track.ReleaseMediaNumber = releaseMediaNumber
                release.LastUpdated = now
                continue
    if release.LastUpdated == now:
        Release.save(release)
    return jsonify(message="OK")



@app.route("/user/release/setrating/<release_id>/<rating>", methods=['POST'])
@login_required
def setUserReleaseRating(release_id, rating):
    try:
        release = Release.objects(id=release_id).first()
        user = User.objects(id=current_user.id).first()
        if not release or not user:
            return jsonify(message="ERROR")
        now = arrow.utcnow().datetime
        userRelease = UserRelease.objects(User=user, Release=release).first()
        if not userRelease:
            userRelease = UserRelease(User=user, Release=release)
        userRelease.Rating = rating
        userRelease.LastUpdated = now
        UserRelease.save(userRelease)
        # Update artist average rating
        releaseAverage = UserRelease.objects(Release=release).aggregate_average('Rating')
        release.Rating = releaseAverage
        release.LastUpdated = now
        Release.save(release)
        return jsonify(message="OK", average=releaseAverage)
    except:
        logger.exception("Error Settings Release Reating")
        return jsonify(message="ERROR")


@app.route("/user/release/toggledislike/<release_id>/<toggle>", methods=['POST'])
@login_required
def toggleUserReleaseDislike(release_id, toggle):
    try:
        release = Release.objects(id=release_id).first()
        user = User.objects(id=current_user.id).first()
        if not release or not user:
            return jsonify(message="ERROR")
        now = arrow.utcnow().datetime
        userRelease = UserRelease.objects(User=user, Release=release).first()
        if not userRelease:
            userRelease = UserRelease(User=user, Release=release)
        userRelease.IsDisliked = toggle.lower() == "true"
        userRelease.LastUpdated = now
        if userRelease.IsDisliked:
            userRelease.Rating = 0
        UserRelease.save(userRelease)
        releaseAverage = UserRelease.objects(Release=release).aggregate_average('Rating')
        if userRelease.IsDisliked:
            # Update release average rating
            release.Rating = releaseAverage
            release.LastUpdated = now
            Release.save(release)
        return jsonify(message="OK", average=releaseAverage)
    except:
        logger.exception("Error Toggling Release Dislike")
        return jsonify(message="ERROR")


@app.route("/user/release/togglefavorite/<release_id>/<toggle>", methods=['POST'])
@login_required
def toggleUserReleaseFavorite(release_id, toggle):
    try:
        release = Release.objects(id=release_id).first()
        user = User.objects(id=current_user.id).first()
        if not release or not user:
            return jsonify(message="ERROR")
        userRelease = UserRelease.objects(User=user, Release=release).first()
        if not userRelease:
            userRelease = UserArtist(User=user, Release=release)
        userRelease.IsFavorite = toggle.lower() == "true"
        userRelease.LastUpdated = arrow.utcnow().datetime
        UserRelease.save(userRelease)
        return jsonify(message="OK")
    except:
        logger.exception("Error Toggling Release Favorite")
        return jsonify(message="ERROR")


@app.route("/artist/rescan/<artist_id>", methods=['POST'])
@login_required
def rescanArtist(artist_id):
    try:
        artist = Artist.objects(id=artist_id).first()
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


@app.route("/release/setTrackCount/<release_id>", methods=['POST'])
@login_required
def setTrackCount(release_id):
    try:
        release = Release.objects(id=release_id).first()
        if not release:
            return jsonify(message="ERROR")
        release.TrackCount = len(release.Tracks)
        Release.save(release)
        return jsonify(message="OK")
    except:
        logger.exception("Error Setting Track Count")
        return jsonify(message="ERROR")

@app.route("/release/setDiscCount/<release_id>", methods=['POST'])
@login_required
def setDiscCount(release_id):
    try:
        release = Release.objects(id=release_id).first()
        if not release:
            return jsonify(message="ERROR")
        discs = []
        for track in release.Tracks:
            if not track.ReleaseMediaNumber in discs:
                discs.append(track.ReleaseMediaNumber)
        release.DiscCount = len(discs)
        Release.save(release)
        return jsonify(message="OK")
    except:
        logger.exception("Error Setting Disc Count")
        return jsonify(message="ERROR")

@app.route("/release/rescan/<release_id>", methods=['POST'])
@login_required
def rescanRelease(release_id):
    try:
        release = Release.objects(id=release_id).first()
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
    release = Release.objects(id=release_id).first()
    if not release:
        return jsonify(message="ERROR")
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for track in release.Tracks:
            path = track.Track.FilePath
            if trackPathReplace:
                for rpl in trackPathReplace:
                    for key, val in rpl.items():
                        path = path.replace(key, val)
            mp3File = os.path.join(path, track.Track.FileName)
            zf.write(mp3File, arcname=track.Track.FileName, compress_type=zipfile.ZIP_DEFLATED)
    memory_file.seek(0)
    zipAttachmentName = release.Artist.Name + " - " + release.Title + ".zip"
    return send_file(memory_file, attachment_filename=zipAttachmentName, as_attachment=True)

@app.route('/artist/delete/<artist_id>', methods=['POST'])
@login_required
def deleteArtist(artist_id):
    artist = Artist.objects(id=artist_id).first()
    if not artist:
        return jsonify(message="ERROR")
    try:
        Artist.delete(artist)
        return jsonify(message="OK")
    except:
        logger.exception("Error Deleting Artist")
        return jsonify(message="ERROR")


@app.route("/artist/deletereleases/<artist_id>", methods=['POST'])
@login_required
def deleteArtistReleases(artist_id):
    artist = Artist.objects(id=artist_id).first()
    if not artist:
        return jsonify(message="ERROR")
    try:
        Track.objects(Artist=artist).delete()
        Release.objects(Artist=artist).delete()
        return jsonify(message="OK")
    except:
        logger.exception("Error Deleting Artist Releases")
        return jsonify(message="ERROR")


@app.route('/release/delete/<release_id>', methods=['POST'])
@login_required
def deleteRelease(release_id):
    release = Release.objects(id=release_id).first()
    if not release:
        return jsonify(message="ERROR")
    try:
        Release.delete(release)
        return jsonify(message="OK")
    except:
        logger.exception("Error Deleting Release")
        return jsonify(message="ERROR")


@app.route("/user/track/setrating/<release_id>/<track_id>/<rating>", methods=['POST'])
@login_required
def setUserTrackRating(release_id, track_id, rating):
    try:
        track = Track.objects(id=track_id).first()
        release = Release.objects(id=release_id).first()
        user = User.objects(id=current_user.id).first()
        if not track or not user:
            return jsonify(message="ERROR")
        now = arrow.utcnow().datetime
        userTrack = UserTrack.objects(User=user, Release=release, Track=track).first()
        if not userTrack:
            userTrack = UserTrack(User=user, Release=release, Track=track)
        userTrack.Rating = rating
        userTrack.LastUpdated = now
        UserTrack.save(userTrack)
        # Update track average rating
        trackAverage = UserTrack.objects(Track=track).aggregate_average('Rating')
        track.Rating = trackAverage
        track.LastUpdated = now
        Track.save(track)
        return jsonify(message="OK", average=trackAverage)
    except:
        logger.exception("Error Setting Track Rating")
        return jsonify(message="ERROR")


@app.route('/releasetrack/delete/<release_id>/<release_track_id>/<flag>', methods=['POST'])
@login_required
def deleteReleaseTrack(release_id, release_track_id, flag):
    try:
        release = Release.objects(id=release_id).first()
        if not release:
            return jsonify(message="ERROR")
        rts = []
        for track in release.Tracks:
            if track.Track.id != objectid.ObjectId(release_track_id):
                rts.append(track)
        release.Tracks = rts
        Release.save(release)

        trackPath = None
        trackFilename = None
        if flag == 't' or flag == "f":
            # Delete the track
            track = Track.objects(id=release_track_id).first()
            if track:
                trackPath = track.FilePath
                trackFilename = os.path.join(track.FilePath, track.FileName)
                Track.delete(track)

        if flag == "f":
            # Delete the file
            try:
                if trackFilename:
                    os.remove(trackFilename)
                # if the folder is empty then delete the folder as well
                if trackPath:
                    if not os.listdir(trackPath):
                        os.rmdir(trackPath)
            except OSError:
                pass

        return jsonify(message="OK")
    except:
        logger.exception("Error Deleting Releae Track")
        return jsonify(message="ERROR")


@app.route('/artist/setimage/<artist_id>/<image_id>', methods=['POST'])
@login_required
def setArtistImage(artist_id, image_id):
    artist = Artist.objects(id=artist_id).first()
    if not artist:
        return jsonify(message="ERROR")

    artistImage = None
    for ai in artist.Images:
        if ai.element.grid_id == objectid.ObjectId(image_id):
            artistImage = ai
            break
    if artistImage:
        image = artistImage.element.read()
        img = Image.open(io.BytesIO(image)).convert('RGB')
        img.thumbnail(thumbnailSize)
        b = io.BytesIO()
        img.save(b, "JPEG")
        bBytes = b.getvalue()
        artist.Thumbnail.new_file()
        artist.Thumbnail.write(bBytes)
        artist.Thumbnail.close()
        artist.LastUpdated = arrow.utcnow().datetime
        Artist.save(artist)
        return jsonify(message="OK")
    return jsonify(message="ERROR")


@app.route('/release/setimage/<release_id>/<image_id>', methods=['POST'])
@login_required
def setReleaseImage(release_id, image_id):
    release = Release.objects(id=release_id).first()
    if not release:
        return jsonify(message="ERROR")

    try:
        releaseImage = None
        for ri in release.Images:
            if ri.element.grid_id == objectid.ObjectId(image_id):
                releaseImage = ri
                break
        if releaseImage:
            image = releaseImage.element.read()
            img = Image.open(io.BytesIO(image)).convert('RGB')
            img.thumbnail(thumbnailSize)
            b = io.BytesIO()
            img.save(b, "JPEG")
            bBytes = b.getvalue()
            release.Thumbnail.new_file()
            release.Thumbnail.write(bBytes)
            release.Thumbnail.close()
            release.LastUpdated = arrow.utcnow().datetime
            Release.save(release)
            return jsonify(message="OK")
    except:
        logger.exception("Error Setting Release Image")
        return jsonify(message="ERROR")


@app.route('/release/<release_id>')
@login_required
def release(release_id):
    release = Release.objects(id=release_id).first()
    if not release:
        return render_template('404.html'), 404
    user = User.objects(id=current_user.id).first()
    userRelease = UserRelease.objects(User=user, Release=release).first()
    collections = Collection.objects(Releases__Release=release).all()
    collectionReleases = []
    if collections:
        for collection in collections:
            for crt in collection.Releases:
                if crt.Release.id == release.id:
                    crt.CollectionId = collection.id
                    crt.CollectionName = collection.Name
                    collectionReleases.append(crt)
    for track in release.Tracks:
        userTrack = UserTrack.objects(User=user, Track=track.Track).first()
        if userTrack:
            track.UserRating = userTrack.Rating
    return render_template('release.html', release=release, collectionReleases=collectionReleases,
                           userRelease=userRelease)


@app.route("/artist/play/<artist_id>/<doShuffle>")
@login_required
def playArtist(artist_id, doShuffle):
    artist = Artist.objects(id=artist_id).first()
    if not artist:
        return render_template('404.html'), 404
    tracks = []
    user = User.objects(id=current_user.id).first()
    for release in Release.objects(Artist=artist):
        for track in sorted(release.Tracks, key=lambda track: (track.ReleaseMediaNumber, track.TrackNumber)):
            tracks.append(M3U.makeTrackInfo(user, release, track.Track))
    if doShuffle == "1":
        random.shuffle(tracks)
    if user.DoUseHTMLPlayer:
        session['tracks'] = tracks
        return player()
    return send_file(M3U.generate(tracks),
                     as_attachment=True,
                     attachment_filename="playlist.m3u")


@app.route("/release/play/<release_id>")
@login_required
def playRelease(release_id):
    release = Release.objects(id=release_id).first()
    if not release:
        return render_template('404.html'), 404
    tracks = []
    user = User.objects(id=current_user.id).first()
    for track in sorted(release.Tracks, key=lambda track: (track.ReleaseMediaNumber, track.TrackNumber)):
        tracks.append(M3U.makeTrackInfo(user, release, track.Track))
    if user.DoUseHTMLPlayer:
        session['tracks'] = tracks
        return player()
    return send_file(M3U.generate(tracks),
                     as_attachment=True,
                     attachment_filename="playlist.m3u")


@app.route("/track/play/<release_id>/<track_id>")
@login_required
def playTrack(release_id, track_id):
    release = Release.objects(id=release_id).first()
    track = Track.objects(id=track_id).first()
    if not release or not track:
        return render_template('404.html'), 404
    tracks = []
    user = User.objects(id=current_user.id).first()
    tracks.append(M3U.makeTrackInfo(user, release, track))
    if user.DoUseHTMLPlayer:
        session['tracks'] = tracks
        return player()
    return send_file(M3U.generate(tracks),
                     as_attachment=True,
                     attachment_filename="playlist.m3u")


@app.route("/que/play", methods=['POST'])
@login_required
def playQue():
    user = User.objects(id=current_user.id).first()
    tracks = []
    for t in request.json:
        if (t["type"] == "track"):
            release = Release.objects(id=t["releaseId"]).first()
            track = Track.objects(id=t["trackId"]).first()
            if release and track:
                tracks.append(M3U.makeTrackInfo(user, release, track))
    if user.DoUseHTMLPlayer:
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
            track = Track.objects(id=t["id"]).first()
            if track:
                tracks.append(track)
    user = User.objects(id=current_user.id).first()
    pl = Playlist.objects(User=user, Name=que_name).first()
    if not pl:
        # adding a new playlist
        pl = Playlist(User=user, Name=que_name, Tracks=tracks)
        Playlist.save(pl)
    else:
        # adding tracks to an existing playlist
        if pl.Tracks:
            for plt in pl.Tracks:
                if plt not in tracks:
                    tracks.append(plt)
        else:
            pl.Tracks = tracks
        Playlist.update(pl)
    return jsonify(message="OK")


@app.route("/stream/track/<user_id>/<release_id>/<track_id>")
def streamTrack(user_id, release_id, track_id):
    if track_id.endswith(".mp3"):
        track_id = track_id[:-4]
    track = Track.objects(id=track_id).first()
    if not track:
        return render_template('404.html'), 404
    track.PlayedCount += 1
    now = arrow.utcnow().datetime
    track.LastPlayed = now
    Track.save(track)
    path = track.FilePath
    if trackPathReplace:
        for rpl in trackPathReplace:
            for key, val in rpl.items():
                path = path.replace(key, val)
    mp3File = os.path.join(path, track.FileName)
    if not os.path.isfile(mp3File):
        print("! Unable To Find Track File [" + mp3File + "]")
        return render_template('404.html'), 404
    (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(mp3File)
    headers = Headers()
    headers.add('Content-Disposition', 'attachment', filename=track.FileName)
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
        headers.add('Content-Range', 'bytes %s-%s/%s' % (str(begin), str(end), str((end - begin)+1)))
    headers.add('Content-Length', str((end - begin) + 1))
    isFullRequest = begin == 0 and (end == (size - 1))
    isEndRangeRequest = begin > 0 and (end != (size - 1))
    # user = None;
    if isFullRequest or isEndRangeRequest and current_user:
        user = User.objects(id=user_id).first()
        if user:
            release = Release.objects(id=release_id).first()
            userRating = 0
            if release:
                userTrack = UserTrack.objects(User=user, Track=track, Release=release).first()
                if not userTrack:
                    userTrack = UserTrack(User=user, Track=track, Release=release)
                userTrack.PlayedCount += 1
                userTrack.LastPlayed = now
                userRating = userTrack.Rating
                UserTrack.save(userTrack)
            try:
                if clients:
                    data = json.dumps({'message': "OK",
                                       'lastPlayedInfo': {
                                           'TrackId': str(track.id),
                                           'TrackTitle': track.Title,
                                           'ReleaseId': str(release.id),
                                           'ReleaseTitle': release.Title,
                                           'ReleaseThumbnail': "/images/release/thumbnail/" + str(release.id),
                                           'ArtistId': str(track.Artist.id),
                                           'ArtistName': track.Artist.Name,
                                           'ArtistThumbnail': "/images/artist/thumbnail/" + str(track.Artist.id),
                                           'UserId': str(user.id),
                                           'Username': user.Username,
                                           'UserThumbnail': "/images/user/avatar/" + str(user.id),
                                           'UserRating': userRating,
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
    logger.debug("Streaming To Ip [" + request.remote_addr + "] Mp3 [" + mp3File + "], Size [" + str(size) + "], Begin [" + str(begin) + "] End [" + str(end) + "]")
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

    topRatedReleases = Release.objects().order_by('-Rating', 'FilePath', 'Title' )[:10]

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
            release = Release.objects(Tracks__Track = track).first()
            tracks.append(M3U.makeTrackInfo(user, release, track))
        if user.DoUseHTMLPlayer:
            session['tracks'] = tracks
            return player()
        return send_file(M3U.generate(tracks),
                         as_attachment=True,
                         attachment_filename="playlist.m3u")
    if option == "top10Albums":
        for release in Release.objects().order_by('-Rating', 'FilePath', 'Title' )[:10]:
            user = User.objects(id=current_user.id).first()
            for track in sorted(release.Tracks, key=lambda track: (track.ReleaseMediaNumber, track.TrackNumber)):
                tracks.append(M3U.makeTrackInfo(user, release, track.Track))
        if user.DoUseHTMLPlayer:
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


@app.route("/images/release/<release_id>/<grid_id>/<height>/<width>")
def getReleaseImage(release_id, grid_id, height, width):
    try:
        release = Release.objects(id=release_id).first()
        releaseImage = None

        if release:
            for ri in release.Images:
                if ri.element.grid_id == objectid.ObjectId(grid_id):
                    releaseImage = ri
                    break

        if releaseImage:
            image = releaseImage.element.read()
            h = int(height)
            w = int(width)
            img = Image.open(io.BytesIO(image)).convert('RGB')
            size = h, w
            img.thumbnail(size)
            b = io.BytesIO()
            img.save(b, "JPEG")
            ba = b.getvalue()
            etag = hashlib.sha1(('%s%s' % (release.id, release.LastUpdated)).encode('utf-8')).hexdigest()
            return makeImageResponse(ba, release.LastUpdated, releaseImage.element.filename, etag)
    except:
        return send_file("static/img/release.gif")


@app.route('/images/artist/<artist_id>/<grid_id>/<height>/<width>')
def getArtistImage(artist_id, grid_id, height, width):
    artist = Artist.objects(id=artist_id).first()
    artistImage = None

    if artist:
        for ai in artist.Images:
            if ai.element.grid_id == objectid.ObjectId(grid_id):
                artistImage = ai
                break

    try:
        if artistImage:
            image = artistImage.element.read()
            h = int(height)
            w = int(width)
            img = Image.open(io.BytesIO(image)).convert('RGB')
            size = h, w
            img.thumbnail(size)
            b = io.BytesIO()
            img.save(b, "JPEG")
            ba = b.getvalue()
            etag = hashlib.sha1(('%s%s' % (artist.id, artist.LastUpdated)).encode('utf-8')).hexdigest()
            return makeImageResponse(ba, artist.LastUpdated, artistImage.element.filename, etag)
    except:
        return send_file("static/img/artist.gif")


@app.route("/images/user/avatar/<user_id>")
def getUserAvatarThumbnailImage(user_id):
    user = User.objects(id=user_id).first()
    try:
        if user:
            image = user.Avatar.read()
            img = Image.open(io.BytesIO(image))
            img.thumbnail(avatarSize)
            b = io.BytesIO()
            img.save(b, "PNG")
            ba = b.getvalue()
            etag = hashlib.sha1(str(user.LastUpdated).encode('utf-8')).hexdigest()
            return makeImageResponse(ba, user.LastUpdated, 'avatar.png', etag, "image/png")
    except:
        return send_file("static/img/user.png",
                         attachment_filename='avatar.png',
                         mimetype='image/png')


@app.route("/images/collection/thumbnail/<collection_id>")
def getCollectionThumbnailImage(collection_id):
    collection = Collection.objects(id=collection_id).first()
    try:
        if collection:
            image = collection.Thumbnail.read()
            img = Image.open(io.BytesIO(image))
            img.thumbnail(thumbnailSize)
            b = io.BytesIO()
            img.save(b, "PNG")
            ba = b.getvalue()
            etag = hashlib.sha1(('%s%s' % (collection.id, collection.LastUpdated)).encode('utf-8')).hexdigest()
            return makeImageResponse(ba, collection.LastUpdated, "a_tn_" + str(collection.id) + ".jpg", etag)

    except:
        return send_file("static/img/collection.gif",
                         attachment_filename='collection.gif',
                         mimetype='image/gif')


@app.route("/images/artist/thumbnail/<artist_id>")
def getArtistThumbnailImage(artist_id):
    artist = Artist.objects(id=artist_id).first()
    try:
        if artist:
            image = artist.Thumbnail.read()
            if not image or len(image) == 0:
                raise RuntimeError("Bad Image Thumbnail")
            etag = hashlib.sha1(('%s%s' % (artist.id, artist.LastUpdated)).encode('utf-8')).hexdigest()
            return makeImageResponse(image, artist.LastUpdated, "a_tn_" + str(artist.id) + ".jpg", etag)

    except:
        return send_file("static/img/artist.gif",
                         attachment_filename='artist.gif',
                         mimetype='image/gif')


@app.route("/images/release/thumbnail/<release_id>")
def getReleaseThumbnailImage(release_id):
    release = Release.objects(id=release_id).first()
    try:
        if release:
            image = release.Thumbnail.read()
            if not image or len(image) == 0:
                raise RuntimeError("Bad Image Thumbnail")
            etag = hashlib.sha1(('%s%s' % (release.id, release.LastUpdated)).encode('utf-8')).hexdigest()
            return makeImageResponse(image, release.LastUpdated, "r_tn_" + str(release.id) + ".jpg", etag)
    except:
        return send_file("static/img/release.gif",
                         attachment_filename='thumbnail.jpg',
                         mimetype='image/jpg')


def jdefault(o):
    if isinstance(o, set):
        return list(o)
    return o.__dict__


@app.route("/images/find/<type>/<type_id>", methods=['POST'])
def findImageForType(type,type_id):
    if type == 'r': # release
        release = Release.objects(id=type_id).first()
        if not release:
            return jsonify(message="ERROR")
        data = []
        searcher = ImageSearcher()
        query = release.Title
        if 'query' in request.form:
            query = request.form['query']
        referer = request.url_root
        gs = searcher.googleSearchImages(referer, request.remote_addr, query)
        if gs:
            for g in gs:
                data.append(g)
        it = searcher.itunesSearchArtistAlbumImages(referer, release.Artist.Name, release.Title)
        if it:
            for i in it:
                data.append(i)
        return Response(json.dumps({'message': "OK", 'query': query, 'data': data}, default=jdefault), mimetype="application/json")
    elif type == 'a': # artist
        return jsonify(message="ERROR")
    else:
        return jsonify(message="ERROR")

@app.route("/release/setCoverViaUrl/<release_id>", methods=['POST'])
def setCoverViaUrl(release_id):
    try:
        release = Release.objects(id=release_id).first()
        if not release:
            return jsonify(message="ERROR")
        url = request.form['url']
        searcher = ImageSearcher()
        imageBytes = searcher.getImageBytesForUrl(url)
        if imageBytes:
            img = Image.open(io.BytesIO(imageBytes)).convert('RGB')
            img.thumbnail(thumbnailSize)
            b = io.BytesIO()
            img.save(b, "JPEG")
            bBytes = b.getvalue()
            release.Thumbnail.new_file()
            release.Thumbnail.write(bBytes)
            release.Thumbnail.close()
            release.LastUpdated = arrow.utcnow().datetime
            Release.save(release)
        return jsonify(message="OK")
    except:
        logger.exception("Error Setting Release Image via Url")
        return jsonify(message="ERROR")


api.add_resource(ArtistApi, '/api/v1.0/artist/<artist_id>')
api.add_resource(ArtistListApi, '/api/v1.0/artists')
api.add_resource(ReleaseListApi, '/api/v1.0/releases')
api.add_resource(TrackListApi, '/api/v1.0/tracks')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(id):
    return User.objects(id=id).first()


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    pwd = bcrypt.generate_password_hash(request.form['password'])
    user = User(Username=request.form['username'],
                Password=pwd,
                Email=request.form['email'],
                RegisteredOn=arrow.utcnow().datetime)
    user.save()
    flash('User successfully registered')
    return redirect(url_for('login'))


@app.route("/profile/edit", methods=['GET', 'POST'])
def editProfile():
    user = User.objects(id=current_user.id).first()
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
    userWithDuplicateEmail = User.objects(Email=email, id__ne=user.id).first()
    if userWithDuplicateEmail:
        flash('Email Address Already Exists!', 'error')
        return redirect(url_for('profile/edit'))
    file = request.files['avatar'];
    if file:
        content = io.BytesIO(file.stream.read())
        img = Image.open(content)
        img.thumbnail(thumbnailSize)
        b = io.BytesIO()
        img.save(b, "PNG")
        user.Avatar.new_file()
        user.Avatar.write(b.getvalue())
        user.Avatar.close()
    if encryptedPassword:
        user.Password = encryptedPassword
    user.Email = email
    user.DoUseHTMLPlayer = doUseHTMLPlayerSet
    user.LastUpdated = arrow.utcnow().datetime
    User.save(user)
    flash('Profile Edited successfully')
    return redirect(url_for("index"))


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
    registered_user = User.objects(Username=username).first()
    if registered_user and bcrypt.check_password_hash(registered_user.Password, password):
        registered_user.LastLogin = arrow.utcnow().datetime
        User.save(registered_user)
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
    user = User.objects(id=current_user.id).first()
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
    collections = Collection.objects().order_by("Name").all()
    notFoundEntryInfos = []
    if 'notFoundEntryInfos' in session:
        notFoundEntryInfos = session['notFoundEntryInfos']
        session['notFoundEntryInfos'] = None
    return render_template('collections.html', collections=collections, notFoundEntryInfos = notFoundEntryInfos)


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
    if 'notFoundEntryInfos' in session:
        notFoundEntryInfos = session['notFoundEntryInfos']
        session['notFoundEntryInfos'] = None
    return render_template('collection.html', collection=collection, counts=counts, notFoundEntryInfos = notFoundEntryInfos)


@app.route("/collection/play/<collection_id>")
@login_required
def playCollection(collection_id):
    collection = Collection.objects(id=collection_id).first()
    if not collection:
        return render_template('404.html'), 404
    user = User.objects(id=current_user.id).first()
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
        for collection in Collection.objects(ListInCSVFormat__ne=None,ListInCSV__ne=None):
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

@app.route("/singletrackreleasefinder", defaults={ 'count': 100 })
@app.route("/singletrackreleasefinder/<count>")
@login_required
def singletrackreleasefinder(count):
    count = int(count)
    singleTrackReleases = Release.objects(__raw__={ 'Tracks' : { '$size': 1}}).order_by('Title', 'Artist.Name')
    return render_template('singletrackreleasefinder.html', total= singleTrackReleases.count(), singleTrackReleases=singleTrackReleases[:count])


@app.route('/dupfinder')
@login_required
def dupFinder():
    artists = []
    for a in Artist.objects():
        artists.append({
            'id' : a.id,
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
                sn =  artist['SortName']
                if sn:
                    artistSortName =sn.lower().strip()
                if (artistName == aName or
                        (aSortname and artistSortName and artistSortName == aSortname) or (artistSortName and artistSortName == aName)) and artist['id'] != a['id']:
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
    def open(self, *args):
        clients.append(self)

    def on_close(self):
        clients.remove(self)


if __name__ == '__main__':
    admin = admin.Admin(app, 'Roadie: Admin', template_mode='bootstrap3')
    admin.add_view(RoadieArtistModelView(Artist))
    admin.add_view(RoadieCollectionModelView(Collection))
    admin.add_view(RoadieModelView(Label))
    admin.add_view(RoadiePlaylistModelView(Playlist))
    admin.add_view(RoadieReleaseModelView(Release))
    admin.add_view(RoadieTrackModelView(Track))
    admin.add_view(RoadieModelAdminRequiredView(User, category='User'))
    admin.add_view(RoadieUserArtistModelView(UserArtist, category='User'))
    admin.add_view(RoadieUserReleaseModelView(UserRelease, category='User'))
    admin.add_view(RoadieUserTrackModelView(UserTrack, category='User'))
    admin.add_view(RoadieModelView(ArtistType, category='Reference Fields'))
    admin.add_view(RoadieModelView(Genre, category='Reference Fields'))
    admin.add_view(RoadieModelView(Quality, category='Reference Fields'))
    admin.add_view(RoadieModelAdminRequiredView(UserRole, category='Reference Fields'))
    container = WSGIContainer(app)
    server = Application([
        (r'/websocket/', WebSocket),
        (r'.*', FallbackHandler, dict(fallback=container))
    ])
    server.listen(5000)
    IOLoop.instance().start()
