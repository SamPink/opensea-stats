import pandas as pd
import datetime as dt


import os, sys


currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)
from opensea.database import read_mongo, write_mongo
from opensea.current_listings import update_current_listings
from opensea.opensea_collections import all_tables


def calc_best_listing(update_listings=True, collection=None):

    # do we want to update the Database
    if update_listings:
        update_current_listings(collection)

    all_in_db = all_tables(collection)

    required_tables = [
        f"{collection}_still_listed",
        f"{collection}_traits",
        f"{collection}_predicted_USD",
    ]

    # check if all_in_db required tables are in the database
    if not all(table in all_in_db for table in required_tables):
        print(f"{collection} is missing some required tables")
        print(f"{all_in_db}")
        return None

    #####find listed apes

    # first get apegang new listed apes
    listing_projection = {
        "_id": 0,
        "asset_id": 1,
        "collection": 1,
        "listing_price": 1,
        "listing_ending": 1,
        "listing_currency": 1,
    }

    listed = read_mongo(
        f"{collection}_still_listed",
        query_projection=listing_projection,
        return_df=True,
    )

    # get eth to usd rate from an external api
    # https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd
    import requests

    url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
    data = requests.get(url).json()

    # get listing usd price
    listed["listing_USD"] = listed["listing_price"] * data["ethereum"]["usd"]

    # drop duplicates on asset_id
    # TODO why dis happen
    listed = listed.drop_duplicates(subset="asset_id")

    # download ape trait info
    apes = read_mongo(
        f"{collection}_traits",
        query_projection={
            "_id": 0,
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

    # if None or .empty
    if ApeGang_USD is None or ApeGang_USD.empty:
        return f"No prediction for {collection}_predicted_USD"

    ApeGang_USD = ApeGang_USD.merge(listed, how="right", on="asset_id")

    ApeGang_USD = ApeGang_USD.merge(apes, how="left", on="asset_id")

    ApeGang_USD["predicted_ETH"] = (
        ApeGang_USD["predicted_USD"] / data["ethereum"]["usd"]
    )

    # filter listing_cuurency == ETH
    ApeGang_USD = ApeGang_USD[ApeGang_USD.listing_currency == "ETH"]

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
