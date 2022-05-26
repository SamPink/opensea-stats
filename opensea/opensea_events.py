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
    search_before=dt.datetime.now(),
    eventType="created",
    collection="boredapeyachtclub",
    api_key="3eb775e344f14798b49718e86f55608c",
    limit=50,
    cursor=None,
):

    # set headers
    headers = {"Accept": "application/json", "X-API-KEY": api_key}

    # convert in search_before to epoch seconds
    if not isinstance(search_before, int):
        search_before = sec_since_epoch(search_before)

    params = {
        "collection_slug": collection,
        "event_type": eventType,
        "only_opensea": "false",
        "limit": limit,
    }
    # if search before param given
    # if cursor is set, add it as param
    if cursor is not None:
        params["cursor"] = cursor

    url = "https://api.opensea.io/api/v1/events"

    response = check_response(method="GET", url=url, headers=headers, params=params)
    return response


# define function to convert from dictionary to opensea events object
def dict_to_events_class(dict, eventType):
    if eventType == "sales":
        return dict_to_sales(dict)
    elif eventType == "listings":
        return dict_to_listing(dict)
    elif eventType == "cancellations":
        return dict_to_canc(dict)
    elif eventType == "transfers":
        return dict_to_transfer(dict)
    else:
        print(
            "no valid eventType, cannot conert dictionary to events class...Dumb Fuck"
        )
        return None


def update_opensea_events(
    collection="boredapeyachtclub",
    eventTypes=["sales", "listings", "transfers", "cancellations"],
    search_dir="forward",
    limit=50,
    update_DB=True,
    overwrite_DB=False,
):

    """
    Get Sales,listings,transfers and cancellations data for a collection from opensea API.

    search_before and search_after parameters, allow time-date filter on Opensea API call.
    """

    if search_dir == "forward":
        # find when database was last updated.
        # Will then call Opensea API, returning events only after this point
        search_before = dict.fromkeys(eventTypes, dt.datetime.now())
        if overwrite_DB == False:
            search_after = get_latest_DB_update(collection)
        if overwrite_DB == True:
            # if overwriting the database, get all data going back to beginning
            search_after = dict.fromkeys(eventTypes, dt.datetime(2000, 1, 1, 0, 0, 0))

    elif search_dir == "backwards":
        search_after = dict.fromkeys(eventTypes, None)
        search_before = get_oldest_DB_update(collection)
    # create dictionary to convert between what we call eventTypes and what opensea calls them...
    eventType_dict = {
        "sales": "successful",
        "transfers": "transfer",
        "listings": "created",
        "cancellations": "cancelled",
    }

    for e in eventTypes:
        print("-----------------------------------------------------------")
        print(f"Getting {collection} {e} data...")

        all_data = []
        i = 0
        events_data = get_opensea_events(
            eventType=eventType_dict[e],
            collection=collection,
            limit=limit,
            search_before=search_before[e],
        )

        while i < 10000:  # infinite loop, continues until no more detail is obtained
            cursor = events_data["next"]
            i += 1

            if events_data is not None and len(events_data["asset_events"]) > 0:
                print(f"{i} API calls made")
                for x in events_data["asset_events"]:
                    events_class_x = dict_to_events_class(dict=x, eventType=e)
                    if events_class_x is None:
                        continue
                    else:
                        if events_class_x.time <= search_after[e]:
                            break  # break inner loop
                        all_data.append(dict(events_class_x))
            else:
                break
            # break outer while loop
            if events_class_x is None or events_class_x.time <= search_after[e]:
                break
            events_data = get_opensea_events(
                eventType=eventType_dict[e],
                collection=collection,
                limit=limit,
                search_before=search_before[e],
                cursor=cursor,
            )

        print(f"{len(all_data)} {e} found.")
        # add data to database if update_DB = True
        if update_DB:
            print(f"write {collection} {e} to MongoDB")
            write_mongo(
                collection=f"{collection}_{e}", data=all_data, overwrite=overwrite_DB
            )
