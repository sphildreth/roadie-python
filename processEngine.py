import os
import json
import argparse
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from resources.processor import Processor
from resources.validator import Validator

p = argparse.ArgumentParser(description='Process Inbound Folders For Updates.')
p.add_argument('--folder', '-f', help='Override library setting in config')
p.add_argument('--dontDeleteInboundFolders', '-d', action='store_true',
               help='Dont Delete Any Processed Inbound Folders')
p.add_argument('--validate', '-vv', action='store_true',
               help='Run Validate Command After Processing')
p.add_argument('--processArtists', '-pa', action='store_true',
               help='Process Artist release folders in Library')
p.add_argument('--flush', '-fl', action='store_true', help='Flush All Releases For Artist Before Processing')
p.add_argument('--readOnly', '-st', action='store_true', help='Read Only Mode; Dont modify Anything')
args = p.parse_args()

d = os.path.dirname(os.path.realpath(__file__)).split(os.sep)
path = os.path.join(os.sep.join(d), "settings.json")
with open(path, "r") as rf:
    config = json.load(rf)

forceFolderScan = False

if args.folder:
    config['ROADIE_INBOUND_FOLDER'] = args.folder
    forceFolderScan = True

engine = create_engine(config['ROADIE_DATABASE_URL'])
conn = engine.connect()
Base = declarative_base()
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()
pp = Processor(config, conn, session, args.readOnly, args.dontDeleteInboundFolders, args.flush)
if args.processArtists:
    pp.processArtists(args.dontValidate)
else:
    pp.process(forceFolderScan=forceFolderScan)
    if not args.validate:
        validator = Validator(config, conn, session, False)
        validator.validateArtists()
