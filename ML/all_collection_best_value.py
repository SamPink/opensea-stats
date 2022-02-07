import pandas as pd
import datetime as dt


import os, sys

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)
from opensea.database import read_mongo, write_mongo
from opensea.current_listings import update_current_listings


def calc_best_listing(update_listings=True, collection=None):

    # do we want to update the Database
    if update_listings:
        update_current_listings(collection)

    #####find listed apes

    # first get apegang new listed apes
    listing_projection = {
        "_id": 0,
        "asset_id": 1,
        "collection": 1,
        "listing_price": 1,
        "listing_ending": 1,
        "listing_currency": 1,
        "listing_USD": 1,
    }

    listed = read_mongo(
        f"{collection}_still_listed",
        query_projection=listing_projection,
        return_df=True,
    )

    # drop duplicates on asset_id
    # TODO why dis happen
    listed = listed.drop_duplicates(subset="asset_id")

    # download ape trait info
    apes = read_mongo(
        f"{collection}_traits",
        query_projection={
            "_id": 0,
            "asset_id": 1,
            "Clothes": 1,
            "Ears": 1,
            "Eyes": 1,
            "Fur": 1,
            "Hat": 1,
            "Mouth": 1,
            "rarity_rank": 1,
        },
        return_df=True,
    )

    # convert apes asset_id to int
    apes["asset_id"] = apes["asset_id"].astype(int)

    ApeGang_USD = read_mongo(
        f"{collection}_predicted_USD",
        # filter for just apes that are listed
        query_filter={"asset_id": {"$in": listed.asset_id.to_list()}},
        query_projection={"_id": 0, "predicted_USD": 1, "asset_id": 1},
        return_df=True,
    )

    ApeGang_USD = ApeGang_USD.merge(listed, how="right", on="asset_id")

    ApeGang_USD = ApeGang_USD.merge(apes, how="left", on="asset_id")

    ApeGang_USD["listing_value"] = ApeGang_USD.predicted_USD / ApeGang_USD.listing_USD

    ApeGang_USD = ApeGang_USD.sort_values("listing_value", ascending=False)

    ApeGang_USD = ApeGang_USD.drop_duplicates(subset="asset_id")

    write_mongo(
        data=ApeGang_USD,
        collection=f"{collection}_bestvalue_opensea_listings",
        overwrite=True,
    )

    print(
        ApeGang_USD.head(10)[
            [
                "asset_id",
                "collection",
                "listing_USD",
                "predicted_USD",
                "listing_value",
                "rarity_rank",
            ]
        ]
    )
