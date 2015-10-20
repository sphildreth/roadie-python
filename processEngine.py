import os
import json
import argparse
from resources.processor import Processor
from resources.validator import Validator

from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine

p = argparse.ArgumentParser(description='Process Inbound and Library Folders For Updates.')
p.add_argument('--dontDeleteInboundFolders', '-d', action='store_true',
               help='Dont Delete Any Processed Inbound Folders')
p.add_argument('--dontValidate', '-dv', action='store_true',
               help='Dont Run Validate Command After Processing')
p.add_argument('--readOnly', '-st', action='store_true', help='Read Only Mode; Dont modify Anything')
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
pp = Processor(config, conn, session, args.readOnly, args.dontDeleteInboundFolders)
pp.process()

if not args.dontValidate:
    validator = Validator(False)
    validator.validateArtists()