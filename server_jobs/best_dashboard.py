import pandas as pd
import opensea.database as db
from opensea.opensea_assets import get_from_collection


def get_urls(collection):
    # TODO the converted asset id should be added into the all database
    asset_cols = get_from_collection(
        collection=collection,
        col_to_return=["image_url", "permalink"],
        id_col="asset_id",
    )
    if asset_cols is None or asset_cols.empty:
        asset_cols = get_from_collection(
            collection=collection,
            col_to_return=["image_url", "permalink"],
        )

    return asset_cols


# TODO needs some kind of logging for jobs
def run_best_dashboard_job():
    all_collections = [
        "cool-cats-nft",
        "the-doge-pound",
        "world-of-women-nft",
        "supducks",
        "cryptoadz-by-gremplin",
        "rumble-kong-league",
        "pepsi-mic-drop",
        "deadfellaz",
        "doodledogsofficial",
        "robotos-official",
        "azuki",
        "alpacadabraz",
    ]

    best = pd.DataFrame()
    for collection in all_collections:
        asset_cols = get_urls(collection)
        df = db.read_mongo(
            f"{collection}_bestvalue_opensea_listings",
            return_df=True,
            query_projection={
                "_id": 0,
                "asset_id": 1,
                "collection": 1,
                "predicted_ETH": 1,
                "listing_price": 1,
                "rarity_rank": 1,
                "image_url": 1,
                "permalink": 1,
            },
            query_sort=[("listing_value", -1)],
            query_limit=1,
        )
        try:
            # join the asset_cols with the best value listings
            df = pd.merge(df, asset_cols, on="asset_id")
            best = best.append(df)
        except Exception as e:
            print(f"{collection} failed: {e}")
            continue

    db.write_mongo(collection="best_dashboard_listings", data=best, overwrite=True)
