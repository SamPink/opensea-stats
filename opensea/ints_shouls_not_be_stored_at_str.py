from database import connect_mongo, read_mongo, write_mongo


database = connect_mongo()
collection = database.collection_names(include_system_collections=False)
for collect in collection:
    # if collect contains _traits
    if "traits" in collect:
        db = read_mongo(collect, return_df=True)

        # convert asset_id to int
        db["asset_id"] = db["asset_id"].astype(int)

        write_mongo(collect, db, overwrite=True)
