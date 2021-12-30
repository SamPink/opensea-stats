import requests
import pandas as pd
import datetime as dt

from class_models import *
from database import *


def sec_since_epoch(time):
    # calculate seconds since epoch of last updated time
    if isinstance(time, str):
        dt_obj = dt.datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%f")
    elif isinstance(time, dt.datetime):
        dt_obj = time
    else:
        raise ValueError(
            "Incorrect dateinput to sec_since_epoch. Use datetime object or %Y-%m-%dT%H:%M:%S.%f format string"
        )
    epoch = dt.datetime(1970, 1, 1, 0, 0, 0)
    return int((dt_obj - epoch).total_seconds())


def get_opensea_asset(
    offset=0, collection="boredapeyachtclub", api_key="3eb775e344f14798b49718e86f55608c"
):

    url = "https://api.opensea.io/api/v1/assets"

    params = {
        "collection_slug": collection,
        "offset": offset * 50,
        "limit": 50,
    }

    headers = {"Accept": "application/json", "X-API-KEY": api_key}

    response = requests.request("GET", url, params=params, headers=headers).json()

    return response


def get_opensea_events(
    lastUpdated=None,
    offset=0,
    eventType="created",
    collection="boredapeyachtclub",
    api_key="3eb775e344f14798b49718e86f55608c",
    limit=50,
):
    if lastUpdated is None:
        lastUpdated = dt.datetime(2000, 1, 1, 0, 0, 0)

    # if integer - take this as seconds since epoch, otherwise calculate seconds since epoch
    if isinstance(lastUpdated, int):
        lastUpdated = lastUpdated
    else:
        lastUpdated = sec_since_epoch(lastUpdated)

    params = {
        "collection_slug": collection,
        "event_type": eventType,
        "only_opensea": "false",
        "occurred_after": lastUpdated,
        "offset": offset * limit,
        "limit": limit,
    }

    headers = {"Accept": "application/json", "X-API-KEY": api_key}

    url = "https://api.opensea.io/api/v1/events"

    response = requests.request("GET", url, params=params, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error in Opensea Events API call. Status code {response.status_code}.")
        return None


def update_opensea_events(
    collection="boredapeyachtclub",
    lastUpdated=None,
    find_lastUpdated_from_DB=True,
    starting_offset=0,
    limit=50,
    update_DB=True,
    overwrite_DB=False,
):

    if lastUpdated is None and find_lastUpdated_from_DB:
        # find when database was last updated. Will then call Opensea API, returning events only after this point
        lastUpdated = get_latest_DB_update(collection)

    """
    Get Sales,listings,transfers and cancellations data for a collection from opensea API
    """
    ###Get sales data from opensea
    all_sales = []
    i = starting_offset  # define iterative variable for offsetting
    print("-----------------------------------------------------------")
    print(f"Getting {collection} sales data...")
    while True:  # infinite loop, continues until no more detail is obtained

        sales = get_opensea_events(
            offset=i,
            eventType="successful",
            collection=collection,
            lastUpdated=lastUpdated,
            limit=limit,
        )
        i += 1  # add 1 to offsetting variable with each loop

        if sales is not None and len(sales["asset_events"]) > 0:
            print(f"{i} API calls made")
            for sale in sales["asset_events"]:
                sale_class = dict_to_sales(sale)
                if sale_class is not None:
                    all_sales.append(dict(sale_class))

        else:
            break
    print(f"{len(all_sales)} sales found.")
    # add data to database if update_DB = True
    if update_DB:
        print("write sales to MongoDB")
        write_mongo(
            collection=f"{collection}_sales", data=all_sales, overwrite=overwrite_DB
        )

    # get data from opensea for NFT transfers
    all_transfers = []
    i = starting_offset
    print("-----------------------------------------------------------")
    print(f"Getting {collection} transfers data...")
    while True:
        transfers = get_opensea_events(
            offset=i,
            eventType="transfer",  # event type for listing is "created"
            collection=collection,
            lastUpdated=lastUpdated,
            limit=limit,
        )
        i += 1  # add 1 to offsetting variable with each loop

        if transfers is not None and len(transfers["asset_events"]) > 0:
            print(f"{i} API calls made")
            for t in transfers["asset_events"]:
                transfer_class = dict_to_transfer(t)
                if transfer_class is not None:
                    all_transfers.append(dict(transfer_class))

        else:
            break
    print(f"{len(all_transfers)} transfers found.")
    # add data to database if update_DB = True
    if update_DB:
        write_mongo(
            collection=f"{collection}_transfers",
            data=all_transfers,
            overwrite=overwrite_DB,
        )

    # Get listings data from opensea
    all_listings = []
    i = starting_offset
    print("-----------------------------------------------------------")
    print(f"Getting {collection} listings data...")

    while True:
        listings = get_opensea_events(
            offset=i,
            eventType="created",  # event type for listing is "created"
            collection=collection,
            lastUpdated=lastUpdated,
            limit=limit,
        )
        i += 1  # add 1 to offsetting variable with each loop

        if listings is not None and len(listings["asset_events"]) > 0:
            print(f"{i} API calls made")
            for auction in listings["asset_events"]:
                list_class = dict_to_listing(auction)
                if list_class is not None:
                    all_listings.append(dict(list_class))
        else:
            break
    print(f"{len(all_listings)} listings found.")
    # add data to database if update_DB = True
    if update_DB:
        write_mongo(
            collection=f"{collection}_listings",
            data=all_listings,
            overwrite=overwrite_DB,
        )

    ## Get cancellation data from opensea
    all_canc = []
    i = starting_offset
    print("-----------------------------------------------------------")
    print(f"Getting {collection} cancellation data...")
    while True:
        canc = get_opensea_events(
            offset=i,
            eventType="cancelled",  # get cancellation data
            collection=collection,
            lastUpdated=lastUpdated,
            limit=limit,
        )
        i += 1  # add 1 to offsetting variable with each loop
        print(f"{i} API calls made")

        if canc is not None and len(canc["asset_events"]) > 0:
            for c in canc["asset_events"]:
                canc_class = dict_to_canc(c)
                if canc_class is not None:
                    all_canc.append(dict(canc_class))
        else:
            break
    print(f"{len(all_canc)} cancellations found.")

    # add data to database if update_DB = True
    if update_DB:
        write_mongo(
            collection=f"{collection}_cancellations",
            data=all_canc,
            overwrite=overwrite_DB,
        )
    else:
        return all_sales, all_transfers, all_listings, all_canc


# test = update_opensea_events(collection="boredapeyachtclub", limit=50, update_DB=True)


def update_current_listings(collection, updateDB=True, find_lastUpdated_from_DB=True):
    # update events for collection
    if updateDB:
        update_opensea_events(
            collection=collection,
            lastUpdated=None,  # if None, will automatically calculate
            limit=50,
            update_DB=True,
            starting_offset=0,
            find_lastUpdated_from_DB=find_lastUpdated_from_DB,
        )

    # define projection without ids - containing just things we need to determine if still listed
    projection = {"_id": 0, "time": 1, "event_type": 1, "asset_id": 1}
    all = pd.DataFrame()  # define empty dataframe
    event_types = ["sales", "listings", "cancellations", "transfers"]
    for e in event_types:
        if e == "listings":  # get all info for listings
            listings = read_mongo(collection=f"{collection}_{e}", return_df=True)
            df = listings.copy()
        else:
            df = read_mongo(
                collection=f"{collection}_{e}",
                query_projection=projection,
                return_df=True,
            )
        all = all.append(df)

    # sort by date
    all = all.sort_values("time")
    # drop duplicates
    last_update = all.drop_duplicates(subset=["asset_id"], keep="last")
    still_listed = last_update[last_update.event_type == "created"]
    # calculate listing ending time
    still_listed["listing_ending"] = still_listed["time"] + pd.to_timedelta(
        still_listed["duration"], "s"
    )
    # keep only listings where listing end is in the future
    still_listed[still_listed.listing_ending > dt.datetime.now()]

    if updateDB:
        write_mongo(
            collection=f"{collection}_still_listed", data=still_listed, overwrite=True
        )
    else:
        return still_listed


collections = [
    "bored-ape-kennel-club",
    "boredapeyachtclub",
    "chromie-squiggle-by-snowfro",
    "cool-cats-nft",
    "cryptoadz-by-gremplin",
    "cryptomories",
    "cyberkongz",
    "guttercatgang",
    "gutterdogs",
    "lazy-lions",
    "mutant-ape-yacht-club",
    "pudgypenguins",
    "the-doge-pound",
    "toucan-gang",
]

for i in collections:
    update_current_listings(collection=i)

print("DONE!")
