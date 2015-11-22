import io
from PIL import Image as PILImage

from sqlalchemy import Column, ForeignKey, LargeBinary, Index, Integer, String
from resources.models.ModelBase import Base


class Image(Base):
    # If this is used then the image is stored in the database
    image = Column(LargeBinary(length=16777215), default=None)
    # If this is used then the image is remote and this is the url
    url = Column(String(500))
    caption = Column(String(100))
    # This is a PhotoHash of the image for assistance in deduping
    signature = Column(String(50))

    artistId = Column(Integer, ForeignKey("artist.id"), index=True)
    releaseId = Column(Integer, ForeignKey("release.id"), index=True)

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

    def __unicode__(self):
        return self.caption

    def __str__(self):
        return self.caption or self.signature
