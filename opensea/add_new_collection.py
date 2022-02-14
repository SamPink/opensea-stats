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

collections = ['']
for nft in collections:
