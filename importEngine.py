import argparse
from importers.collectionImporter import CollectionImporter

p = argparse.ArgumentParser(description='Import Various Records.')
p.add_argument('--readOnly', '-st', action='store_true', help='Read Only Mode; Dont modify Anything')
p.add_argument('--type', '-t', help="Type To Import", required=True)
p.add_argument('--id', '-n', help="Id Of Type To Import", required=True)
p.add_argument('--filename', '-f', help="CSV Filename To Import", required=True)
p.add_argument('--format', '-fmt', help="CSV Format; position, artist, album", required=True)
args = p.parse_args()

if str(args.type).lower() == "collection":
    c = CollectionImporter(args.id, args.readOnly, args.format, args.filename)


