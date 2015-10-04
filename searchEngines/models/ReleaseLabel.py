from searchEngines.models.ModelBase import ModelBase


class ReleaseLabel(ModelBase):
    catalogNumber = None
    beginDate = None
    endDate = None
    release = None
    label = None

    def __init__(self, label, release, catalogNumber=None):
        self.label = label
        self.release = release
        self.catalogNumber = catalogNumber

    def __unicode__(self):
        return self.label.name + " (" + self.beginDate.strfttime('%Y') + ")"
