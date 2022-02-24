import pandas as pd
from pymongo import MongoClient
import pymongo
import ssl

database_name = "mvh"
# url = "mongodb+srv://mvh:W1xIlKbF46rFCsiM@cluster0.ecrau.mongodb.net/mvh?authSource=admin&replicaSet=atlas-pxb4a1-shard-0&w=majority&readPreference=primary&appname=mongodb-vscode%200.7.0&retryWrites=true&ssl=true"
url = "mongodb://documentDBone:xNSwXT35i4fejwm@docdb-2022-02-21-18-03-57.cluster-cscdvnycycj7.eu-west-2.docdb.amazonaws.com:27017/?replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false"


def connect_mongo():
    my_client = MongoClient(url, ssl_cert_reqs=ssl.CERT_NONE)
    my_db = my_client[database_name]
    return my_db


def count_documents(collection, query_filter={}, url=url, database_name=database_name):
    my_client = MongoClient(url)
    my_db = my_client[database_name]
    my_collection = my_db[collection]
    n_docs = my_collection.count_documents(filter=query_filter)
    return n_docs


def write_mongo(
    collection, data, overwrite=False, database_name=database_name, url=url
):
    """Wrapper for the mongoDB .insert_many() function to add to the database

    Args:
        collection ([str]): name of the mongoDB collection
        data ([dataframe or list of dict]): [description]
        overwrite (bool, optional): [description]. Defaults to False.
    """
    my_client = MongoClient(url)
    my_db = my_client[database_name]
    my_collection = my_db[collection]

    #
    if overwrite:
        n_docs = my_collection.count_documents({})
        print(f"deleting {n_docs} from {collection} mongoDB collection.")
        my_collection.delete_many({})  # delete all data

    if isinstance(data, pd.DataFrame):
        # convert dataframe back to list of dictionaries
        data = data.to_dict("records")

    # write data to collection
    if len(data) > 1 and isinstance(data, list):
        try:
            my_collection.insert_many(data, ordered=False)

            print(f"updating {collection} with {len(data)} documents.")

            my_collection.create_index("asset_id")
            return "inserted"

        except pymongo.errors.BulkWriteError as e:
            panic = list(filter(lambda x: x["code"] != 11000, e.details["writeErrors"]))

            if len(panic) > 0:
                raise e

            inserted_no = len(data) - len(e.details["writeErrors"])
            # only return duplicate is no rows inserted
            if inserted_no == 0:
                return "duplicate"

            print(f"updating {collection} with {inserted_no}")

            return "inserted"
        except Exception as e:
            return e


def read_mongo(
    collection,
    return_id=False,
    query_filter={},
    query_projection=[],
    query_sort=[],
    query_limit=None,
    database_name=database_name,
    url=url,
    return_df=False,
):

    my_client = MongoClient(url)
    my_db = my_client[database_name]
    if collection not in my_db.list_collection_names():
        print(
            f"Collection '{collection}' doesn't exist.\nPlease select one of the following; {my_db.list_collection_names()[0:4]}"
        )
        return None
    my_collection = my_db[collection]

    # if no projection input, defult to all columns
    if len(query_projection) < 1:
        query_projection = my_collection.find_one().keys()

    if return_id is False and not isinstance(query_projection, dict):
        query_projection = dict.fromkeys(query_projection, 1)
        query_projection["_id"] = 0

    # if no limit input, set to all documents
    if query_limit is None:
        query_limit = my_collection.count_documents({})

    # Make a query to the specific DB and Collection
    data = list(
        my_collection.find(
            filter=query_filter,
            projection=query_projection,
            sort=query_sort,
            limit=query_limit,
        )
    )

    if len(data) > 0:
        if return_df:
            data = pd.DataFrame(data)
        return data
    else:  # return None if no data found
        print(f"No data found for {collection} with specific query - {query_filter}")
        return None


def get_latest_DB_update(
    collection, eventTypes=["sales", "transfers", "listings", "cancellations"]
):

    projection = ["time"]
    sorting = [("time", -1)]
    recent_updates = {}
    for event in eventTypes:
        recent_update = read_mongo(
            collection=f"{collection}_{event}",
            query_projection=projection,
            query_sort=sorting,
            query_limit=1,
        )
        if recent_update is not None:
            recent_updates[event] = recent_update[0]["time"]
        else:
            recent_updates[event] = None

    if len(recent_updates) > 0:
        return recent_updates
    else:
        return None


def get_oldest_DB_update(
    collection, eventTypes=["sales", "transfers", "listings", "cancellations"]
):

    projection = ["time"]
    sorting = [("time", 1)]
    oldest_updates = {}
    for event in eventTypes:
        oldest_entry = read_mongo(
            collection=f"{collection}_{event}",
            query_projection=projection,
            query_sort=sorting,
            query_limit=1,
        )
        if oldest_entry is not None:
            oldest_updates[event] = oldest_entry[0]["time"]
        else:
            oldest_updates[event] = None

    if len(oldest_updates) > 0:
        return oldest_updates
    else:
        return None
