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
    aws_db = db.connect_mongo()
    all_collections = aws_db.list_collection_names()

    # filter all_collections to only include collections that have "bestvalue_opensea_listings" in the name
    all_collections = [
        collection
        for collection in all_collections
        if "bestvalue_opensea_listings" in collection
    ]

    best = pd.DataFrame()
    for collection in all_collections:
        print(collection)
        asset_cols = get_urls(collection.replace("_bestvalue_opensea_listings", ""))
        df = db.read_mongo(
            f"{collection}",
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
