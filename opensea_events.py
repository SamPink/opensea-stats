import requests
import pandas as pd
import datetime as dt

from class_models import *


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


def update_opensea_events(collection="boredapeyachtclub", lastUpdated=None, limit=50):
    """
    Get Sales data for a collection from opensea API
    """
    ###Get sales data from opensea
    all_sales = []
    i = 0  # define iterative variable for offsetting
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
            for sale in sales["asset_events"]:
                all_sales.append(dict_to_sales(sale))

        else:
            break
    print(f"{len(all_sales)} sales found.")

    # get data from opensea for NFT transfers
    all_transfers = []
    i = 0
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
            for t in transfers["asset_events"]:
                all_transfers.append(dict_to_transfer(t))

        else:
            break
    print(f"{len(all_transfers)} transfers found.")

    # Get listings data from opensea
    all_listings = []
    i = 0
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
            for auction in listings["asset_events"]:
                all_listings.append(dict_to_listing(auction))
        else:
            break
    print(f"{len(all_listings)} listings found.")
    #### TO DO - append to database


test = update_opensea_events(
    lastUpdated=dt.datetime(2021, 12, 26, 0, 0, 0),
    collection="boredapeyachtclub",
    limit=50,
)


"""def get_opensea_cancellations(collection="boredapeyachtclub"):
    all_cancs = []
    i = 0
    while True:
        canc = get_opensea_events(
            offset=i,
            eventType="cancelled",  # event type for listing is "created"
            collection=collection,
        )

        i += 1  # add 1 to offsetting variable with each loop
        print(f"Getting cancellations for {collection}, {i} calls performed.")
        if canc is not None and len(canc["asset_events"]) > 0:
            for c in canc["asset_events"]:
                # if acction for bundle, pull out all asset ids
                if int(c["quantity"]) > 1 and c["asset_bundle"] is not None:
                    asset_id = [d["token_id"] for d in c["asset_bundle"]["assets"]]
                elif c["quantity"] == "1":
                    asset_id = c["asset"]["token_id"]
                else:
                    asset_id = None

                canc_i = {
                    "listing_id": c["id"],
                    "asset_id": asset_id,
                    "collection": c["collection_slug"],
                    "time": c["created_date"],
                    "event_type": c["event_type"],
                    "seller_address": c["seller"]["address"],
                }
                all_cancs.append(canc_i)
        else:
            return all_cancs
"""
