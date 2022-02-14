import pandas as pd
import os, sys


currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)
from opensea.database import *
from opensea.opensea_events import *
from opensea.opensea_assets import *
from opensea.current_listings import *
from ML.train_collection_x_ML import *

collections = [
    "superrare",
    "clonex",
    "hapeprime",
    "livesofasuna",
    "lookatmyraccoon",
    "nft-worlds",
    "karafuru",
    "grandpaapecountryclub",
    "forgottenruneswizardscult",
    "cryptocoven",
    "lostpoets",
    "sneaky-vampire-syndicate",
    "ghxsts",
]
for nft in collections:
    get_collection_assets(nft)
    update_opensea_events(nft)
    for i in range(8):
        update_opensea_events(
            nft,
            find_lastUpdated_from_DB=False,
            find_firstUpdated_from_DB=True,
        )
    update_current_listings(nft)
    collection_autoML(nft)
