class PathInfo(object):
    def __init__(self, artistName, releaseYear, releaseTitle):
        self.artistName = artistName
        self.releaseYear = releaseYear
        self.releaseTitle = releaseTitle

    def __str__(self):
        return str(self.artistName) + " [" + str(self.releaseYear) + "] " + str(self.releaseTitle)
