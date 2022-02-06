from opensea.database import read_mongo


def read_sales(collection, count):
    projection = {
        "_id": 0,
        "asset_id": 1,
        "image_url": 0,
        "time": 1,
    }

    df = read_mongo(
        "{collection}_sales",
        query_limit=count,
        query_sort=[("time", -1)],
        query_projection=projection,
        return_df=True,
    )    
    return df
