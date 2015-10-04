from searchEngines.models.ModelBase import ModelBase


class Genre(ModelBase):
    name = None

    def __init__(self, name):
        self.name = name

    def __unicode__(self):
        return self.name
