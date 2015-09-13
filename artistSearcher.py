import argparse
from resources.artistSearcher import ArtistSearcher

p = argparse.ArgumentParser(description='Search For Artist Information.')
p.add_argument('--name', '-n', help="Artist Name", required=True)
p.add_argument('--release', '-r', help="Release Title", required=False)
args = p.parse_args()

with ArtistSearcher() as s:
    artistInfo = s.iTunesArtist(args.name)
    if artistInfo:
        print("Artist Info: " + str(artistInfo))
        albums = s.iTunesAlbumsForArtist(artistInfo)
        if albums:
            print("Artist Albums Count [" + str(len(albums)) + "]")
            for album in albums:
                if args.release and album.title.lower() == args.release.lower():
                    print("Release Info [" + str(album) + "]")
                elif not args.release:
                    print("Release Info [" + str(album) + "]")
        else:
            print("No Releases Found!")
    else:
        print("Artist Not Found!")


