import os, sys


currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)
from opensea.database import *
from opensea.opensea_events import *
from opensea.opensea_collections import *


x = all_collection_names()[::-1]
for nft in x:
    for i in range(8):
        update_opensea_events(
            nft,
            find_lastUpdated_from_DB=False,
            find_firstUpdated_from_DB=True,
        )
