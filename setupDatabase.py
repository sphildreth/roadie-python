import os
import json
import logging

from sqlalchemy import create_engine

from resources.models.ModelBase import Base

d = os.path.dirname(os.path.realpath(__file__)).split(os.sep)
path = os.path.join(os.sep.join(d), "settings.json")
with open(path, "r") as rf:
    config = json.load(rf)

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)

engine = create_engine(config['ROADIE_DATABASE_URL'])
Base.metadata.create_all(engine)
