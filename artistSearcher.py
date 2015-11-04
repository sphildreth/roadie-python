import os
import json
import argparse

from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy import create_engine

from resources.common import *
from factories.artistFactory import ArtistFactory
from factories.releaseFactory import ReleaseFactory

p = argparse.ArgumentParser(description='Search For Artist Information.')
p.add_argument('--name', '-n', help="Artist Name", required=True)
p.add_argument('--forceRefresh', '-f', action='store_true', help="Force search again from Search Engines",
               required=False)
p.add_argument('--release', '-r', help="Release Title", required=False)
p.add_argument('--showMissing', '-s', action='store_true', help="Show Releases Not Found In Roadie Database",
               required=False)
args = p.parse_args()

d = os.path.dirname(os.path.realpath(__file__)).split(os.sep)
path = os.path.join(os.sep.join(d), "settings.json")
with open(path, "r") as rf:
    config = json.load(rf)

engine = create_engine(config['ROADIE_DATABASE_URL'])
conn = engine.connect()
Base = declarative_base()
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

artistFactory = ArtistFactory(conn, session)
releaseFactory = ReleaseFactory(conn, session)

start = arrow.utcnow()
artist = artistFactory.get(args.name)
if artist:
    elapsed = arrow.utcnow() - start
    uprint("Artist Info [Elapsed Time: " + str(elapsed) + "]: " + artist.info())
    releaseName = args.release
    if releaseName:
        start = arrow.utcnow()
        release = releaseFactory.get(artist, args.release, False, args.forceRefresh)
        elapsed = arrow.utcnow() - start
        if release:
            uprint("Release Info [Elapsed Time: " + str(elapsed) + "]: " + str(release.info()) + "]")
        else:
            print("No Release(s) Found!")
    else:
        start = arrow.utcnow()
        releases = releaseFactory.getAllForArtist(artist)
        elapsed = arrow.utcnow() - start
        if releases:
            uprint("Releases Info(s) [Elapsed Time: " + str(elapsed) + "]")
            for release in releases:
                uprint(release.info())
        else:
            print("No Release(s) Found!")
else:
    print("Artist Not Found!")
