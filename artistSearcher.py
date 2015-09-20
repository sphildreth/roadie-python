import argparse
from resources.artistSearcher import ArtistSearcher

p = argparse.ArgumentParser(description='Search For Artist Information.')
p.add_argument('--name', '-n', help="Artist Name", required=True)
p.add_argument('--release', '-r', help="Release Title", required=False)
p.add_argument('--showMissing', '-s', action='store_true', help="Show Releases Not Found In Roadie Database", required=False)
args = p.parse_args()

with ArtistSearcher(None) as s:
    artistInfo = s.searchForArtist(args.name)
    if artistInfo:
        print("Artist Info: " + str(artistInfo))
        releases = s.searchForArtistReleases(artistInfo, args.release)
        if releases:
            missing = 0
            for release in releases:
                if not release.roadieId or release.roadieId == "None":
                    missing += 1
            print("Artist Releases Count [" + str(len(releases)) + "] Missing [" + str(missing) + "]")
            for release in releases:
                if args.showMissing and not release.roadieId or release.roadieId == "None":
                    print("[Missing] Release Info [" + str(release) + "]")
                elif not args.showMissing:
                    print("Release Info [" + str(release) + "]")
        else:
            print("No Release(s) Found!")
    else:
        print("Artist Not Found!")


