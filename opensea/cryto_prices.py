import pandas as pd
from Historic_Crypto import HistoricalData
import datetime as dt

import os, sys

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)
from opensea.database import read_mongo, write_mongo


def update_eth_usd():
    last_update = read_mongo(
        collection="eth-usd",
        query_projection={"time": 1, "_id": 0},
        query_sort=[("time", -1)],
        query_limit=1,
    )[0]["time"]

    # convert last update to string
    start_query = (last_update + dt.timedelta(minutes=1)).strftime("%Y-%m-%d-%H-%M")

    eth_usd = HistoricalData("ETH-USD", 3600, start_query).retrieve_data()

    eth_usd["time"] = eth_usd.index

    eth_usd = eth_usd[["time", "close"]]

    eth_usd = eth_usd.rename(columns={"close": "eth-usd-rate"})

    write_mongo("eth-usd", eth_usd)
