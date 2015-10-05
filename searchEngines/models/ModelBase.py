import uuid


class ModelBase(object):

    roadieId = None
    tags = None
    alternateNames = None
    urls = None

    def __init__(self):
        self.roadieId = str(uuid.uuid4())
        self.tags = []
        self.alternateNames = []
        self.urls = []
