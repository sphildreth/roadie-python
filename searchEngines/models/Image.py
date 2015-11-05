import io
from PIL import Image as PILImage
from searchEngines.models.ModelBase import ModelBase


class Image(ModelBase):
    # If this is used then the image is stored in the database
    image = None
    # If this is used then the image is remote and this is the url
    url = None
    caption = None

    artistId = 0
    releaseId = 0

    def averageHash(self):
        try:
            hash_size = 8
            # Open the image, resize it and convert it to black & white.
            image = PILImage.open(io.BytesIO(self.image)).resize((hash_size, hash_size), PILImage.ANTIALIAS).convert(
                'L')
            pixels = list(image.getdata())
            # Compute the hash based on each pixels value compared to the average.
            avg = sum(pixels) / len(pixels)
            bits = "".join(map(lambda pixel: '1' if pixel > avg else '0', pixels))
            hashformat = "0{hashlength}x".format(hashlength=hash_size ** 2 // 4)
            return int(bits, 2).__format__(hashformat)
        except:
            return None

    def __init__(self, url):
        self.url = url
        super(Image, self).__init__()

    def __unicode__(self):
        return self.caption
