import os
import json
import logging
from sqlalchemy import create_engine
# These need to be here for SQlAlchemy to setup the DB to read MetaData
from resources.models.ModelBase import Base
from resources.models.Artist import Artist
from resources.models.Collection import Collection
from resources.models.CollectionRelease import CollectionRelease
from resources.models.Genre import Genre
from resources.models.Image import Image
from resources.models.Label import Label
from resources.models.Playlist import Playlist
from resources.models.PlaylistTrack import PlaylistTrack
from resources.models.Release import Release
from resources.models.ReleaseLabel import ReleaseLabel
from resources.models.ReleaseMedia import ReleaseMedia
from resources.models.Track import Track
from resources.models.User import User
from resources.models.UserArtist import UserArtist
from resources.models.UserRelease import UserRelease
from resources.models.UserRole import UserRole
from resources.models.UserTrack import UserTrack

d = os.path.dirname(os.path.realpath(__file__)).split(os.sep)
path = os.path.join(os.sep.join(d), "settings.json")
with open(path, "r") as rf:
    config = json.load(rf)

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)

engine = create_engine(config['ROADIE_DATABASE_URL'])
Base.metadata.create_all(engine)
