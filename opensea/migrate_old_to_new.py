from database import connect_mongo, read_mongo, write_mongo
from pymongo import MongoClient
import pandas as pd
import pymongo
import ssl

url_old = "mongodb+srv://ape-gang:SW68cArWhOdB4Fhx@cluster0.sryj9.mongodb.net/ape_gang?authSource=admin&replicaSet=atlas-ja5kmb-shard-0&w=majority&readPreference=primary&retryWrites=true&ssl=true"
my_client = MongoClient(url_old, ssl_cert_reqs=ssl.CERT_NONE)
my_db = my_client["mvh"]

database = connect_mongo()

collection = my_db.collection_names(include_system_collections=False)
for collect in collection:
    # if collect contains _traits
    if "traits" in collect:
        db = read_mongo(collect, return_df=True, url=url_old)

        # if colum tokken_id exists convert to asset_id
        if "token_id" in db.columns:
            db = db.rename(columns={"token_id": "asset_id"})

        # if asset_id is not int
        if not db["asset_id"].dtype == "int64":
            db["asset_id"] = db["asset_id"].astype(int)

        write_mongo(collect, db, overwrite=True)
