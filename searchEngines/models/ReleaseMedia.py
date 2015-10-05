from searchEngines.models.ModelBase import ModelBase


class ReleaseMedia(ModelBase):
    # The cd number ie cd x of x
    releaseMediaNumber = -1
    # Any potential subtitle of cd x of x; see 'Star Time' from James Brown
    releaseSubTitle = None
    # Number of Tracks that should be on the Release Media
    trackCount = 0
    # Tracks For The Release Media
    tracks = []

    # The Release for the Release Media
    release = None

    def __init__(self, releaseMediaNumber):
        self.releaseMediaNumber = releaseMediaNumber
        super(ReleaseMedia, self).__init__()

    def __unicode__(self):
        return self.release.title + " " + self.releaseMediaNumber

    def mergeWithReleaseMedia(self, right):

        """

        :type right: ReleaseMedia
        """
        result = self
        if not right:
            return result
        result.releaseMediaNumber = result.releaseMediaNumber or right.releaseMediaNumber
        result.releaseSubTitle = result.releaseSubTitle or right.releaseSubTitle
        result.trackCount = result.trackCount or right.trackCount
        if not result.tracks and right.tracks:
            result.tracks = right.tracks
        elif result.tracks and right.tracks:
            mergedTracks = []
            for track in result.tracks:
                rightTrack = [t for t in result.tracks if t.trackNumber == track.trackNumber];
                if rightTrack:
                    mergedTracks.append(track.mergeWithTrack(rightTrack[0]))
                else:
                    mergedTracks.append(track)
            result.tracks = mergedTracks
        return result
