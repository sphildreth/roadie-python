import io
import os
import hashlib
import json
import datetime
from bson import objectid
from PIL import Image
from flask import Flask, jsonify, render_template, send_file, Response, request, \
    flash, url_for, redirect, abort, session, abort, g
import flask_admin as admin
from flask_restful import Api
from flask_mongoengine import MongoEngine
from resources.artistApi import ArtistApi
from resources.artistListApi import ArtistListApi
from resources.models import Artist, ArtistType, Genre, Label, \
    Quality, Release, ReleaseLabel, Track, TrackRelease, User, UserArtist, UserRole, UserTrack
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

app = Flask(__name__)
app.jinja_env.filters['format_tracktime'] = format_tracktime
app.jinja_env.filters['format_timedelta'] = format_timedelta

with open(os.path.join(app.root_path, "settings.json"), "r") as rf:
    config = json.load(rf)
app.config.update(config)
thumbnailSize = config['ROADIE_THUMBNAILS']['Height'], config['ROADIE_THUMBNAILS']['Width']
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
    return render_template('home.html')


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
    return render_template('release.html', release=release)


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
            return send_file(io.BytesIO(ba),
                             attachment_filename=artistImage.element.filename,
                             mimetype='image/jpg')
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
            rv = send_file(io.BytesIO(ba),
                           attachment_filename='avatar.png',
                           conditional=True,
                           mimetype='image/png')
            rv.last_modified = user.LastUpdated
            rv.make_conditional(request)
            rv.set_etag(etag)
            return rv
    except:
        return send_file("static/img/user.png",
                         attachment_filename='avatar.png',
                         mimetype='image/png')


@app.route("/images/artist/thumbnail/<artist_id>")
def getArtistThumbnailImage(artist_id):
    artist = Artist.objects(id=artist_id).first()
    try:
        if artist:
            image = artist.Thumbnail.read()
            bytes = io.BytesIO(image)
            if not bytes or len(image) == 0:
                raise RuntimeError("Bad Image Thumbnail")
            return send_file(bytes,
                             attachment_filename='thumbnail.jpg',
                             mimetype='image/jpg')
    except:
        return send_file("static/img/artist.gif",
                         attachment_filename='thumbnail.jpg',
                         mimetype='image/jpg')


@app.route("/images/release/thumbnail/<release_id>")
def getReleaseThumbnailImage(release_id):
    release = Release.objects(id=release_id).first()
    try:
        if release:
            image = release.Thumbnail.read()
            bytes = io.BytesIO(image)
            if not bytes or len(image) == 0:
                raise RuntimeError("Bad Image Thumbnail")
            return send_file(bytes,
                             attachment_filename='thumbnail.jpg',
                             mimetype='image/jpg')
    except:
        return send_file("static/img/release.gif",
                         attachment_filename='thumbnail.jpg',
                         mimetype='image/jpg')


api.add_resource(ArtistApi, '/api/v1.0/artist/<artist_id>')
api.add_resource(ArtistListApi, '/api/v1.0/artists')

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
                RegisteredOn=datetime.datetime.now())
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
    admin.add_view(RoadieModelView(Label))
    admin.add_view(RoadieReleaseModelView(Release))
    admin.add_view(RoadieTrackModelView(Track))
    admin.add_view(RoadieModelView(User))
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
