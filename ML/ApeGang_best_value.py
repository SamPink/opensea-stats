import pandas as pd
import datetime as dt


import os, sys

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)
from opensea.database import read_mongo, write_mongo
from opensea.current_listings import update_current_listings


def calc_best_apegang_listing(update_listings=True):

    # do we want to update the Database
    if update_listings:
        # update apegang events
        for i in ["ape-gang", "ape-gang-old"]:
            update_current_listings(i)

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

    ape_gang_new_listed = read_mongo(
        "ape-gang_still_listed", query_projection=listing_projection, return_df=True
    )

    ape_gang_old_listed = read_mongo(
        "ape-gang-old_still_listed",
        query_projection=listing_projection,
        return_df=True,
    )
    # merge new and old collections together
    AG_listed = ape_gang_new_listed.append(ape_gang_old_listed)

    # download ape trait info
    apes = read_mongo(
        "ape-gang-old_traits",
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

    ApeGang_USD = (
        read_mongo(
            "ape-gang-USD-value",
            # filter for just apes that are listed
            query_filter={"asset_id": {"$in": AG_listed.asset_id.to_list()}},
            query_projection={"_id": 0, "pred_USD": 1, "asset_id": 1},
            return_df=True,
        )
        .merge(AG_listed, how="right", on="asset_id")
        .merge(apes, how="left", on="asset_id")
    )

    #
    ApeGang_USD["listing_value"] = ApeGang_USD.pred_USD / ApeGang_USD.listing_USD

    ApeGang_USD = ApeGang_USD.sort_values("listing_value", ascending=False)

    # drop duplicates on asset_id
    ApeGang_USD = ApeGang_USD.drop_duplicates(subset="asset_id")

    write_mongo(
        data=ApeGang_USD,
        collection="ape-gang_bestvalue_opensea_listings",
        overwrite=True,
    )

    print(
        ApeGang_USD.head(10)[
            [
                "asset_id",
                "collection",
                "listing_USD",
                "pred_USD",
                "listing_value",
                "rarity_rank",
            ]
        ]
    )
