import argparse
from resources.artistSearcher import ArtistSearcher

p = argparse.ArgumentParser(description='Search For Artist Information.')
p.add_argument('--name', '-n', help="Artist Name", required=True)
p.add_argument('--release', '-r', help="Release Title", required=False)
args = p.parse_args()

with ArtistSearcher() as s:
    artistInfo = s.searchForArtist(args.name)
    if artistInfo:
        print("Artist Info: " + str(artistInfo))
        releases = s.searchForArtistReleases(artistInfo, args.release)
        if releases:
            print("Artist Releases Count [" + str(len(releases)) + "]")
            for releases in releases:
                print("Release Info [" + str(releases) + "]")
        else:
            print("No Releases Found!")
    else:
        print("Artist Not Found!")


