import pandas as pd
from Historic_Crypto import HistoricalData
import os, sys

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)
from opensea.database import *
from opensea.opensea_events import *


def update_current_listings(collection, update_DB=True, find_lastUpdated_from_DB=True):
    # update events for collection
    if collection == "cryptopunks":
        print("no cryptopunk listing data available from opensea")
        return None

    if update_DB:
        update_opensea_events(
            collection=collection,
            search_after=None,  # if None, will automatically calculate
            limit=50,
            update_DB=True,
            starting_offset=0,
            find_lastUpdated_from_DB=find_lastUpdated_from_DB,
        )

    # define projection without ids - containing just things we need to determine if still listed
    projection = {"_id": 0, "time": 1, "event_type": 1, "asset_id": 1}
    all = pd.DataFrame()  # define empty dataframe
    event_types = ["sales", "listings", "cancellations", "transfers"]
    for e in event_types:
        ## get all info for listings - that are dutch and public
        if e == "listings":
            listings = read_mongo(
                collection=f"{collection}_{e}",
                query_filter={"private_auction": False, "auction_type": "dutch"},
                return_df=True,
            )
            df = listings.copy()
        else:
            df = read_mongo(
                collection=f"{collection}_{e}",
                query_projection=projection,
                return_df=True,
            )
        all = all.append(df)

    # sort by date
    all = all.sort_values("time")
    # drop duplicates
    last_update = all.drop_duplicates(subset=["asset_id"], keep="last")
    still_listed = last_update[last_update.event_type == "created"]
    # calculate listing ending time
    still_listed["listing_ending"] = still_listed["time"] + pd.to_timedelta(
        still_listed["duration"], "s"
    )
    # keep only listings where listing end is in the future
    still_listed = still_listed[still_listed.listing_ending > dt.datetime.now()]

    if collection == "ape-gang-old":
        migrated_apes = read_mongo(
            "ape-gang_traits",
            query_projection={"_id": 0, "asset_id": 1},
            return_df=True,
        )
        # remove migrated apes from still listed
        still_listed = still_listed[~still_listed.asset_id.isin(migrated_apes.asset_id)]

    print(f"{collection} is listed {still_listed.shape[0]}")

    if update_DB:
        write_mongo(
            collection=f"{collection}_still_listed", data=still_listed, overwrite=True
        )
    else:
        return still_listed


"""
collections = [
    "ape-gang",
    "ape-gang-old",
    "boredapeyachtclub",
    "bored-ape-kennel-club",
    "mutant-ape-yacht-club",
    "chromie-squiggle-by-snowfro",
    "cool-cats-nft",
    "cryptoadz-by-gremplin",
    "cryptomories",
    "guttercatgang",
    "toucan-gang",
    "the-doge-pound",
]
for nfts in collections:
    update_current_listings(collection=nfts)
"""
