import argparse
from resources.processor import Processor

p = argparse.ArgumentParser(description='Process Inbound and Library Folders For Updates.')
p.add_argument('--dontDeleteInboundFolders', '-d', action='store_true',
               help='Dont Delete Any Processed Inbound Folders')
p.add_argument('--readOnly', '-st', action='store_true', help='Read Only Mode; Dont modify Anything')
args = p.parse_args()

pp = Processor(args.readOnly, args.dontDeleteInboundFolders)
pp.process()

