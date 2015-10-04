import os
import json
import argparse

import arrow
from sqlalchemy import create_engine

from sqlalchemy.orm import sessionmaker

from searchEngines.artistSearcher import ArtistSearcher
from resources.models.ModelBase import Base

p = argparse.ArgumentParser(description='Search For Artist Information.')
p.add_argument('--name', '-n', help="Artist Name", required=True)
p.add_argument('--release', '-r', help="Release Title", required=False)
p.add_argument('--showMissing', '-s', action='store_true', help="Show Releases Not Found In Roadie Database", required=False)
args = p.parse_args()

d = os.path.dirname(os.path.realpath(__file__)).split(os.sep)
path = os.path.join(os.sep.join(d), "settings.json")
with open(path, "r") as rf:
    config = json.load(rf)

engine = create_engine(config['ROADIE_DATABASE_URL'], echo=True)

start = arrow.utcnow()
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
dbSession = DBSession()
s = ArtistSearcher(dbSession)
artist = s.searchForArtist(args.name)
if artist:
    elapsed = arrow.utcnow() - start
    print("Artist Info [Elapsed Time: " + str(elapsed) + "]: " + artist.info())
    releases = s.searchForArtistReleases(artist, args.release)
    if releases:
        missing = 0
        for release in releases:
            if not release.roadieId or release.roadieId == "None":
                missing += 1
        print("Artist Releases Count [" + str(len(releases)) + "] Missing [" + str(missing) + "]")
        for release in releases:
            if args.showMissing and not release.roadieId or release.roadieId == "None":
                print("[Missing] Release Info [" + str(release) + "]")
            elif not args.showMissing:
                print("Release Info [" + str(release) + "]")
    else:
        print("No Release(s) Found!")
else:
    print("Artist Not Found!")
