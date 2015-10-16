import codecs
import os
import json
import argparse

import arrow
from sqlalchemy import create_engine

from mongoengine import connect
from resources.mongoModels import Artist, Release, Track, UserTrack

from resources.common import *

#from searchEngines.artistSearcher import ArtistSearcher
import sys
from factories.artistFactory import ArtistFactory


p = argparse.ArgumentParser(description='Search For Artist Information.')
p.add_argument('--name', '-n', help="Artist Name", required=True)
p.add_argument('--release', '-r', help="Release Title", required=False)
p.add_argument('--showMissing', '-s', action='store_true', help="Show Releases Not Found In Roadie Database",
               required=False)
args = p.parse_args()

d = os.path.dirname(os.path.realpath(__file__)).split(os.sep)
path = os.path.join(os.sep.join(d), "settings.json")
with open(path, "r") as rf:
    config = json.load(rf)

dbName = config['MONGODB_SETTINGS']['DB']
host = config['MONGODB_SETTINGS']['host']
mongoClient = connect(dbName, host=host)

engine = create_engine(config['ROADIE_DATABASE_URL'], echo=True)

start = arrow.utcnow()


for artist in Artist.objects()[:200]:
    uprint(deriveArtistFromName(artist.Name))

f = ArtistFactory(config)
artist = f.get(args.name)
uprint(artist.info())


# s = ArtistSearcher()
# artist = s.searchForArtist(args.name)
# if artist:
#     elapsed = arrow.utcnow() - start
#     print("Artist Info [Elapsed Time: " + str(elapsed) + "]: " + artist.info())
#     start = arrow.utcnow()
#     releases = s.searchForArtistReleases(artist, args.release)
#     elapsed = arrow.utcnow() - start
#     if releases:
#         missing = 0
#         print(
#             "Artist Releases [Elapsed Time: " + str(elapsed) + "]: Count [" + str(len(releases)) + "] Missing [" + str(
#                 missing) + "]")
#         for release in releases:
#             if args.showMissing and not release.roadieId or release.roadieId == "None":
#                 print("[Missing] Release Info [" + str(release.info()) + "]")
#             elif not args.showMissing:
#                 print("Release Info [" + str(release.info()) + "]")
#     else:
#         print("No Release(s) Found!")
# else:
#     print("Artist Not Found!")
