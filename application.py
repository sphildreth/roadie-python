import io
import os
import json
import datetime
from PIL import Image
from flask import Flask, render_template, send_file, Response, request,\
                  flash, url_for, redirect, abort, session, abort, g
import flask_admin as admin
from flask_admin.contrib.mongoengine import ModelView
from flask_restful import Api
from flask_mongoengine import MongoEngine
from resources.artistApi import ArtistApi
from resources.artistListApi import ArtistListApi
from resources.models import Artist, ArtistType, Genre, Label,\
                             Quality, Release, Track, User, UserRole
from flask.ext.mongoengine import MongoEngineSessionInterface
from flask.ext.login import LoginManager, login_user, logout_user,\
                            current_user, login_required
from flask.ext.bcrypt import Bcrypt
from tornado.wsgi import WSGIContainer
from tornado.web import Application, FallbackHandler
from tornado.websocket import WebSocketHandler
from tornado.ioloop import IOLoop


app = Flask(__name__)
with open(os.path.join(app.root_path, "settings.json"), "r") as rf:
    config = json.load(rf)
app.config.update(config)
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
    return render_template('artist.html', artist=artist)

@app.route("/images/artist/thumbnail/<artist_id>")
def getArtistThumbnailImage(artist_id):
    artist = Artist.objects(id=artist_id).first()

    try:
        if artist:
            image = artist.Thumbnail.read()
            return send_file(io.BytesIO(image),
                         attachment_filename='thumbnail.jpg',
                         mimetype='image/jpg')
    except:
        return send_file("static/img/artist.gif")


@app.route("/images/release/thumbnail/<release_id>")
def getReleaseThumbnailImage(release_id):
    release = Release.objects(id=release_id).first()
    try:
        if release:
            image = release.Thumbnail.read()
            return send_file(io.BytesIO(image),
                         attachment_filename='thumbnail.jpg',
                         mimetype='image/jpg')
    except:
        return send_file("static/img/release.gif")


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


class RoadieModelView(ModelView):

    def is_accessible(self):
        if not current_user.is_active() or not current_user.is_authenticated():
            return False

        if current_user.has_role('Admin'):
            return True

        return False


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
    admin.add_view(RoadieModelView(Release))
    admin.add_view(RoadieModelView(Track))
    admin.add_view(RoadieModelView(User))
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
