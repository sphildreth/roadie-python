import os
import json
import argparse
import sys
import codecs
from resources.processor import Processor
from resources.validator import Validator
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from importers.collectionImporter import CollectionImporter

if sys.stdout.encoding != 'cp850':
    sys.stdout = codecs.getwriter('cp850')(sys.stdout.buffer, 'strict')
if sys.stderr.encoding != 'cp850':
    sys.stderr = codecs.getwriter('cp850')(sys.stderr.buffer, 'strict')

p = argparse.ArgumentParser(description='Import Various Records.')
p.add_argument('--readOnly', '-st', action='store_true', help='Read Only Mode; Dont modify Anything')
p.add_argument('--type', '-t', help="Type To Import", required=True)
p.add_argument('--id', '-n', help="Id Of Type To Import", required=True)
p.add_argument('--filename', '-f', help="CSV Filename To Import", required=True)
p.add_argument('--format', '-fmt', help="CSV Format; position, artist, album", required=True)
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

if str(args.type).lower() == "collection":
    c = CollectionImporter(conn, session, args.id, args.readOnly, args.format, args.filename)
