import requests
import pandas as pd
import datetime as dt
import time

import os, sys

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)
from opensea.class_models import *
from opensea.database import *
from opensea.opensea_assets import check_response


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


def get_opensea_events(
    search_after=None,
    search_before=None,
    offset=0,
    eventType="created",
    collection="boredapeyachtclub",
    api_key="3eb775e344f14798b49718e86f55608c",
    limit=50,
):
    if search_after is None:
        search_after = dt.datetime(2000, 1, 1, 0, 0, 0)

    if search_before is None:
        search_before = dt.datetime.now()

    # if integer - take this as seconds since epoch, otherwise calculate seconds since epoch
    if isinstance(search_after, int):
        search_after = search_after
    else:
        search_after = sec_since_epoch(search_after)

    # convert in search_before to epoch seconds
    if isinstance(search_before, int):
        search_before = search_before
    else:
        search_before = sec_since_epoch(search_before)

    params = {
        "collection_slug": collection,
        "event_type": eventType,
        "only_opensea": "false",
        "occurred_after": search_after,
        "occurred_before": search_before,
        "offset": offset * limit,
        "limit": limit,
    }

    headers = {"Accept": "application/json", "X-API-KEY": api_key}

    url = "https://api.opensea.io/api/v1/events"

    response = check_response(method="GET", url=url, headers=headers, params=params)
    return response


def update_opensea_events(
    collection="boredapeyachtclub",
    eventTypes=["sales", "listings", "transfers", "cancellations"],
    search_after=None,
    find_lastUpdated_from_DB=True,
    search_before=None,
    find_firstUpdated_from_DB=False,
    starting_offset=0,
    limit=50,
    update_DB=True,
    overwrite_DB=False,
):

    """
    Get Sales,listings,transfers and cancellations data for a collection from opensea API.

    search_before and search_after parameters, allow time-date filter on Opensea API call.
    """

    if find_lastUpdated_from_DB and find_firstUpdated_from_DB:
        raise Exception(
            "You have selected automatically update search_before AND search_after from database. Must be done 1 at a time!"
        )

    if search_after is None and find_lastUpdated_from_DB:
        # find when database was last updated.
        # Will then call Opensea API, returning events only after this point
        search_after = get_latest_DB_update(collection)
    else:
        search_after = dict.fromkeys(eventTypes, None)

    if search_before is None and find_firstUpdated_from_DB:
        # find when the first database entry is
        # call opensea for events occuring before this time
        search_before = get_oldest_DB_update(collection)
    else:
        search_before = dict.fromkeys(eventTypes, None)

    ###Get sales data from opensea
    if "sales" in eventTypes:
        all_sales = []
        i = starting_offset  # define iterative variable for offsetting
        print("-----------------------------------------------------------")
        print(f"Getting {collection} sales data...")
        while True:  # infinite loop, continues until no more detail is obtained

            sales = get_opensea_events(
                offset=i,
                eventType="successful",
                collection=collection,
                search_after=search_after["sales"],
                search_before=search_before["sales"],
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
    if "transfers" in eventTypes and collection != "cryptopunks":
        all_transfers = []
        opensea_burn = "0x000000000000000000000000000000000000dead"
        i = starting_offset
        print("-----------------------------------------------------------")
        print(f"Getting {collection} transfers data...")
        while True:
            transfers = get_opensea_events(
                offset=i,
                eventType="transfer",  # event type for listing is "created"
                collection=collection,
                search_after=search_after["transfers"],
                search_before=search_before["transfers"],
                limit=limit,
            )
            i += 1  # add 1 to offsetting variable with each loop

            if transfers is not None and len(transfers["asset_events"]) > 0:
                print(f"{i} API calls made")
                for t in transfers["asset_events"]:
                    # don't register transfers to burn address
                    if (
                        MultiLevelNoneToStr(t, ["transaction", "to_account", "address"])
                        is not opensea_burn
                    ):
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
    if "listings" in eventTypes and collection != "cryptopunks":

        all_listings = []
        i = starting_offset
        print("-----------------------------------------------------------")
        print(f"Getting {collection} listings data...")

        while True:
            listings = get_opensea_events(
                offset=i,
                eventType="created",  # event type for listing is "created"
                collection=collection,
                search_after=search_after["listings"],
                search_before=search_before["listings"],
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

    if "cancellations" in eventTypes:

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
                search_after=search_after["cancellations"],
                search_before=search_before["cancellations"],
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
