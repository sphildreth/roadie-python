from searchEngines.models.ModelBase import ModelBase


class Label(ModelBase):
    name = None
    sortName = None
    musicBrainzId = None
    beginDate = None
    endDate = None
    imageUrl = None
    releases = []

    def __init__(self, name, sortName=None):
        self.name = name
        self.sortName = sortName

    def __unicode__(self):
        return self.name

    def info(self):
        return "Id [" + str(self.id) + "], RoadieId [" + str(self.roadieId) + "], MusicBrainzId [" + str(
            self.musicBrainzId) + "], Name [" + str(self.name) + \
               "AlternateNames [" + str(len(self.alternateNames or [])) + "], Tags [" + str(len(self.tags or [])) + "]"
