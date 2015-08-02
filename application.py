import arrow
import io
import os
import hashlib
import json
import random
from time import time
from bson import objectid
from PIL import Image
from flask import Flask, jsonify, render_template, send_file, Response, request, \
    flash, url_for, redirect, abort, session, abort, g
import flask_admin as admin
from flask_restful import Api
from flask_mongoengine import MongoEngine
from resources.artistApi import ArtistApi
from resources.artistListApi import ArtistListApi
from resources.releaseListApi import ReleaseListApi
from resources.models import Artist, ArtistType, Collection, CollectionRelease, Genre, Label, \
    Playlist, Quality, Release, ReleaseLabel, Track, TrackRelease, User, UserArtist, UserRole, UserTrack
from resources.m3u import M3U
from flask.ext.mongoengine import MongoEngineSessionInterface
from flask.ext.login import LoginManager, login_user, logout_user, \
    current_user, login_required
from flask.ext.bcrypt import Bcrypt
from tornado.wsgi import WSGIContainer
from tornado.web import Application, FallbackHandler
from tornado.websocket import WebSocketHandler
from tornado.ioloop import IOLoop
from operator import itemgetter
from resources.nocache import nocache
from resources.jinjaFilters import format_tracktime, format_timedelta
from viewModels.RoadieModelView import RoadieModelView
from viewModels.RoadieReleaseModelView import RoadieReleaseModelView
from viewModels.RoadieTrackModelView import RoadieTrackModelView
from viewModels.RoadieCollectionModelView import RoadieCollectionModelView
from viewModels.RoadieUserModelView import RoadieUserModelView
from werkzeug.datastructures import Headers
from re import findall

app = Flask(__name__)
app.jinja_env.filters['format_tracktime'] = format_tracktime
app.jinja_env.filters['format_timedelta'] = format_timedelta

with open(os.path.join(app.root_path, "settings.json"), "r") as rf:
    config = json.load(rf)
app.config.update(config)
thumbnailSize = config['ROADIE_THUMBNAILS']['Height'], config['ROADIE_THUMBNAILS']['Width']
trackPathReplace = None
if 'ROADIE_TRACK_PATH_REPLACE' in config:
    trackPathReplace = config['ROADIE_TRACK_PATH_REPLACE']
avatarSize = 30, 30

db = MongoEngine(app)
app.session_interface = MongoEngineSessionInterface(db)
flask_bcrypt = Bcrypt(app)
bcrypt = Bcrypt()
api = Api(app)


@app.before_request
def before_request():
    g.user = current_user


@app.route('/')
def index():
    lastPlayedInfos = []
    for ut in UserTrack.objects().order_by('-LastPlayed')[:25]:
        info = {
            'TrackId' : str(ut.Track.id),
            'TrackTitle' : ut.Track.Title,
            'ReleaseId' : str(ut.Release.id),
            'ReleaseTitle' : ut.Release.Title,
            'ReleaseThumbnail' : "/images/release/thumbnail/" + str(ut.Release.id),
            'ArtistId' : str(ut.Track.Artist.id),
            'ArtistName' : ut.Track.Artist.Name,
            'ArtistThumbnail' : "/images/artist/thumbnail/" + str(ut.Track.Artist.id),
            'UserId' : str(ut.User.id),
            'Username' : ut.User.Username,
            'UserThumbnail' : "/images/user/avatar/" + str(ut.User.id),
            'LastPlayed' : arrow.get(ut.LastPlayed).humanize()
        }
        lastPlayedInfos.append(info)

    return render_template('home.html', lastPlayedInfos = lastPlayedInfos)


@app.route('/artist/<artist_id>')
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
    for t in totalTime:
        counts['length'] = t['total']
    return render_template('artist.html', artist=artist, releases=releases, counts=counts)


@app.route('/artist/delete/<artist_id>', methods=['POST'])
def deleteArtist(artist_id):
    artist = Artist.objects(id=artist_id).first()
    if not artist:
        return jsonify(message="ERROR")
    try:
        Artist.delete(artist)
        return jsonify(message="OK")
    except:
        return jsonify(message="ERROR")


@app.route('/release/delete/<release_id>', methods=['POST'])
def deleteRelease(release_id):
    release = Release.objects(id=release_id).first()
    if not release:
        return jsonify(message="ERROR")
    try:
        Release.delete(release)
        return jsonify(message="OK")
    except:
        return jsonify(message="ERROR")


@app.route('/releasetrack/delete/<release_id>/<release_track_id>/flag', methods=['POST'])
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

        trackFilename = None
        if flag == 't' or flag == "f":
            # Delete the track
            track = Track.objects(id=release_track_id).first()
            if track:
                trackFilename = os.path.join(track.FilePath, track.FileName)
                Track.delete(track)

        if flag == "f":
            # Delete the file
            try:
                os.remove(trackFilename)
            except OSError:
                pass

        return jsonify(message="OK")
    except:
        return jsonify(message="ERROR")


@app.route('/artist/setimage/<artist_id>/<image_id>', methods=['POST'])
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
        Artist.save(artist)
        return jsonify(message="OK")
    return jsonify(message="ERROR")


@app.route('/release/<release_id>')
def release(release_id):
    release = Release.objects(id=release_id).first()
    if not release:
        return render_template('404.html'), 404
    collections = Collection.objects(Releases__Release=release).all()
    collectionReleases = []
    if collections:
        for collection in collections:
            for crt in collection.Releases:
                if crt.Release.id == release.id:
                    crt.CollectionId = collection.id
                    crt.CollectionName = collection.Name
                    collectionReleases.append(crt)

    return render_template('release.html', release=release, collectionReleases= collectionReleases)

@app.route("/artist/play/<artist_id>/<doShuffle>")
def playArtist(artist_id,doShuffle):
    artist = Artist.objects(id=artist_id).first()
    if not artist:
        return render_template('404.html'), 404
    tracks = []
    user = User.objects(id=current_user.id).first()
    for release in Release.objects(Artist=artist):
        for track in sorted(release.Tracks, key=lambda track: (track.ReleaseMediaNumber,  track.TrackNumber)):
            tracks.append(M3U.makeTrackInfo(user,release, track.Track))
    if doShuffle == "1":
        random.shuffle(tracks)
    return send_file(M3U.generate(tracks),
                     as_attachment=True,
                     attachment_filename= "playlist.m3u")

@app.route("/release/play/<release_id>")
def playRelease(release_id):
    release = Release.objects(id=release_id).first()
    if not release:
        return render_template('404.html'), 404
    tracks = []
    user = User.objects(id=current_user.id).first()
    for track in sorted(release.Tracks, key=lambda track: (track.ReleaseMediaNumber,  track.TrackNumber)):
        tracks.append(M3U.makeTrackInfo(user,release, track.Track))
    return send_file(M3U.generate(tracks),
                     as_attachment=True,
                     attachment_filename="playlist.m3u")

@app.route("/track/play/<release_id>/<track_id>")
def playTrack(release_id, track_id):
    release = Release.objects(id=release_id).first()
    track = Track.objects(id=track_id).first()
    if not release or not track:
        return render_template('404.html'), 404
    tracks = []
    user = User.objects(id=current_user.id).first()
    tracks.append(M3U.makeTrackInfo(user, release, track))
    return send_file(M3U.generate(tracks),
                 as_attachment=True,
                 attachment_filename="playlist.m3u")

@app.route("/que/play", methods=['POST'])
def playQue():
    user = User.objects(id=current_user.id).first()
    tracks = []
    for t in request.json:
        if(t["type"] == "track"):
            release = Release.objects(id=t["releaseId"]).firts()
            track = Track.objects(id=t["trackId"]).first()
            if release and track:
                tracks.append(M3U.makeTrackInfo(user,release, track))
    return send_file(M3U.generate(tracks),
                     as_attachment=True,
                     attachment_filename="playlist.m3u")


@app.route("/que/save/<que_name>", methods=['POST'])
def saveQue(que_name):
    if not que_name or not current_user:
        return jsonify(message="ERROR")
    tracks = []
    for t in request.json:
        if(t["type"] == "track"):
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
            for key,val in rpl.items():
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
        headers.add('Content-Range', 'bytes %s-%s/%s' % (str(begin), str(end), str(end - begin)))
    headers.add('Content-Length', str((end - begin) + 1))
    isFullRequest = begin == 0 and (end == (size - 1))
    isEndRangeRequest = begin > 0 and (end != (size -1))
    if isFullRequest or isEndRangeRequest and current_user:
        user = User.objects(id=user_id).first()
        if user:
            release = Release.objects(id=release_id).first()
            if release:
                userTrack = UserTrack.objects(User=user, Track=track, Release=release).first()
                if not userTrack:
                    userTrack = UserTrack(User=user, Track=track, Release=release)
                userTrack.PlayedCount += 1
                userTrack.LastPlayed = now
                UserTrack.save(userTrack)
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
    return response


@app.route('/stats')
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

    mostRecentReleases = Release.objects().order_by('-ReleaseDate', 'Title', 'Artist.SortName')[:10]

    return render_template('stats.html', top10Artists=sorted(top10Artists.items(), key=itemgetter(1), reverse=True)
                           , top10ArtistsByTracks=sorted(top10ArtistsTracks.items(), key=itemgetter(1), reverse=True)
                           , mostRecentReleases=mostRecentReleases
                           , counts=counts)


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
            image = user.Avatar.element.read()
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
            return makeImageResponse(ba, collection.LastUpdated, "a_tn_" + str(collection.id) +".jpg", etag)

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
            return makeImageResponse(image, artist.LastUpdated, "a_tn_" + str(artist.id) +".jpg", etag)

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
            return makeImageResponse(image, release.LastUpdated, "r_tn_" + str(release.id) +".jpg", etag)
    except:
        return send_file("static/img/release.gif",
                         attachment_filename='thumbnail.jpg',
                         mimetype='image/jpg')


api.add_resource(ArtistApi, '/api/v1.0/artist/<artist_id>')
api.add_resource(ArtistListApi, '/api/v1.0/artists')
api.add_resource(ReleaseListApi, '/api/v1.0/releases')

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


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    username = request.form['username']
    password = request.form['password']
    remember_me = False
    if 'remember_me' in request.form:
        remember_me = True
    registered_user = User.objects(Username=username).first()
    if registered_user and bcrypt.check_password_hash(registered_user.Password, password):
        login_user(registered_user, remember=remember_me)
        flash('Logged in successfully')
        return redirect(request.args.get('next') or url_for('index'))
    else:
        flash('Username or Password is invalid', 'error')
        return redirect(url_for('login'))


@app.route('/scanStorage')
def scanStorage():
    return render_template('scanStorage.html')

@app.route('/playlists')
def playlists():
    user = User.objects(id=current_user.id).first()
    userPlaylists = Playlist.objects(User=user).order_by("Name").all()
  #  sharedPlaylists =  Playlist.objects(User__ne = user).all() #.order_by('User__Name', 'Name').all()
    return render_template('playlist.html', userPlaylists=userPlaylists) #, sharedPlaylists=sharedPlaylists)


@app.route("/collections")
def collections():
    collections = Collection.objects().order_by("Name").all()
    return render_template('collections.html', collections=collections)

@app.route('/collection/<collection_id>')
def collection(collection_id):
    collection = Collection.objects(id=collection_id).first()
    if not collection:
        return render_template('404.html'), 404
    return render_template('collection.html', collection=collection)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


class ScannerSocket(WebSocketHandler):
    def open(self):
        print("Socket opened.")

    def on_message(self, message):
        self.write_message("Received: " + message)
        print("Received message: " + message)

    def on_close(self):
        print("Socket closed.")


if __name__ == '__main__':
    admin = admin.Admin(app, 'Roadie: Admin', template_mode='bootstrap3')
    admin.add_view(RoadieModelView(Artist))
    admin.add_view(RoadieCollectionModelView(Collection))
    admin.add_view(RoadieModelView(Label))
    admin.add_view(RoadieReleaseModelView(Release))
    admin.add_view(RoadieTrackModelView(Track))
    admin.add_view(RoadieUserModelView(User))
    admin.add_view(RoadieModelView(UserArtist))
    admin.add_view(RoadieModelView(UserTrack))
    admin.add_view(RoadieModelView(ArtistType, category='Reference Fields'))
    admin.add_view(RoadieModelView(Genre, category='Reference Fields'))
    admin.add_view(RoadieModelView(Quality, category='Reference Fields'))
    admin.add_view(RoadieModelView(UserRole, category='Reference Fields'))
    container = WSGIContainer(app)
    server = Application([
        (r'/scanner/', ScannerSocket),
        (r'.*', FallbackHandler, dict(fallback=container))
    ])
    server.listen(5000)
    IOLoop.instance().start()
