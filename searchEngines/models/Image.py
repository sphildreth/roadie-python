from searchEngines.models.ModelBase import ModelBase


class Image(ModelBase):
    # If this is used then the image is stored in the database
    image = None
    # If this is used then the image is remote and this is the url
    url = None
    caption = None

    artistId = 0
    releaseId = 0

    def __init__(self, url):
        self.url = url
        super(Image, self).__init__()

    def __unicode__(self):
        return self.caption
