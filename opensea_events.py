import requests
import pandas as pd
import datetime as dt


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
        "offset": offset * 50,
        "limit": 50,
    }

    headers = {"Accept": "application/json", "X-API-KEY": api_key}

    url = "https://api.opensea.io/api/v1/events"

    response = requests.request("GET", url, params=params, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error in Opensea Events API call. Status code {response.status_code}.")
        return None


response = get_opensea_events(
    eventType="successful",
    collection="boredapeyachtclub",
)


def get_opensea_sales(collection="boredapeyachtclub", lastUpdated=None):
    """
    Get Sales data for a collection from opensea API
    """
    all_sales = []
    i = 0
    while True:
        print(i)
        sales = get_opensea_events(
            offset=i,
            eventType="successful",
            collection=collection,
            lastUpdated=lastUpdated,
        )
        i += 1  # add 1 to offsetting variable with each loop

        if sales is not None and len(sales["asset_events"]) > 0:
            for sale in sales["asset_events"]:
                # is item single or a bundle
                if int(sale["quantity"]) > 1:
                    asset_df = pd.DataFrame(sale["asset_bundle"]["assets"])
                    asset_id = asset_df["token_id"].to_list()
                    asset_url = asset_df["image_url"].to_list()
                elif sale["quantity"] == "1":
                    asset_id = sale["asset"]["token_id"]
                    asset_url = sale["asset"]["image_url"]
                sale_price = int(sale["total_price"]) / 1e18
                USD_conv = float(sale["payment_token"]["usd_price"])
                USD_price = sale_price * USD_conv
                sale_i = {
                    "sale_id": sale["id"],
                    # info about NFT itself
                    "id": asset_id,
                    "sale_quantity": sale["quantity"],
                    "collection": sale["collection_slug"],
                    "image_url": asset_url,
                    # info about transcation
                    "time": sale["created_date"],
                    "event_type": sale["event_type"],
                    "seller_wallet": sale["seller"]["address"],
                    "buyer_wallet": sale["winner_account"]["address"],
                    "block_hash": sale["transaction"]["block_hash"],
                    # info about sale price
                    "sale_currency": sale["payment_token"]["symbol"],
                    "sale_price": sale_price,
                    "curr_to_USD": USD_conv,
                    "USD_price": USD_price,
                }
                all_sales.append(sale_i)
        else:
            return all_sales


BAYC_all = pd.DataFrame(get_opensea_sales(collection="boredapeyachtclub"))
BAYC_today = pd.DataFrame(
    get_opensea_sales(
        collection="boredapeyachtclub", lastUpdated=dt.datetime(2021, 12, 28, 0, 0, 0)
    )
)


def get_opensea_listings(collection="boredapeyachtclub"):

    all_listings = []
    i = 0
    while True:

        listings = get_opensea_events(
            offset=i,
            eventType="created",  # event type for listing is "created"
            collection=collection,
        )

        i += 1  # add 1 to offsetting variable with each loop
        print(f"Getting listings for {collection}, {i} calls performed.")
        if listings is not None and len(listings["asset_events"]) > 0:
            for l in listings["asset_events"]:
                # if acction for bundle, pull out all asset ids
                if int(l["quantity"]) > 1 and l["asset_bundle"] is not None:
                    asset_id = [d["token_id"] for d in l["asset_bundle"]["assets"]]
                elif l["quantity"] == "1":
                    asset_id = l["asset"]["token_id"]
                else:
                    asset_id = None

                listing_i = {
                    "listing_id": l["id"],
                    "asset_id": asset_id,
                    "collection": l["collection_slug"],
                    "event_type": l["event_type"],
                    "time": l["created_date"],
                    "seller_address": l["seller"]["address"],
                    "listing_price": int(l["ending_price"]) / 1e18,
                }
                all_listings.append(listing_i)
        else:
            return all_listings


def get_opensea_cancellations(collection="boredapeyachtclub"):
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


listings = pd.DataFrame(get_opensea_listings())
cancs = pd.DataFrame(get_opensea_cancellations())

both = listings.append(cancs)
# sort by time
both = both.sort_values("time", ascending=False)
# keep most recent update
