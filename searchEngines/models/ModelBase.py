import uuid


class ModelBase(object):
    roadieId = None
    tags = []
    alternateNames = []
    urls = []

    def __init__(self):
        self.roadieId = str(uuid.uuid4())
