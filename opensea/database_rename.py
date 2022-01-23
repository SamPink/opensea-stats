from database import connect_mongo


database = connect_mongo()
collection = database.collection_names(include_system_collections=False)
for collect in collection:
    # if collect contains _traits
    if "traits" in collect:
        # get colum names from collection
        col_names = database[collect].find_one().keys()
        # if col_names contains token_id
        if "token_id" in col_names:
            # rename token_id to asset_id
            database[collect].update_many({}, {"$rename": {"token_id": "asset_id"}})
