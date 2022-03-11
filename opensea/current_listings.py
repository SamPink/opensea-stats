from asyncore import read
from mimetypes import read_mime_types
import pandas as pd
import datetime as dt
import os, sys


currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)
from opensea.database import *
from opensea.opensea_events import *


def update_current_listings(collection):
    # get list of database collections
    database = connect_mongo()
    db_collections = database.collection_names(include_system_collections=False)

    if f"{collection}_listings" not in db_collections:
        print(f"No listings found for {collection}")
        update_opensea_events(
            collection=collection,
            eventTypes=["sales", "transfers"],
            search_dir="forward",
            limit=50,
            update_DB=True,
        )
        return None
    else:
        update_opensea_events(
            collection=collection,
            search_dir="forward",  # if None, will automatically calculate
            limit=50,
            update_DB=True,
        )

    # define projection without ids - containing just things we need to determine if still listed
    projection = ["time", "event_type", "asset_id", "sale_price"]
    all = pd.DataFrame()  # define empty dataframe
    event_types = ["sales", "listings", "cancellations", "transfers"]
    for e in event_types:
        ## get all info for listings - that are dutch and public
        if e == "listings":
            listings = read_mongo(
                collection=f"{collection}_{e}",
                query_filter={
                    "private_auction": False,
                    "auction_type": "dutch",
                    "listing_currency": {"$in": ["ETH", "WETH"]},
                },
                return_df=True,
            )
            # some listings with crazy durations, set anything over 10 years to 10 years
            ten_yr_in_sec = 3.156e8
            listings.loc[
                listings["duration"] > ten_yr_in_sec, "duration"
            ] = ten_yr_in_sec
            listings["duration"] = pd.to_timedelta(listings["duration"], "s")

            listings["listing_ending"] = listings["time"] + listings["duration"]
            df = listings.copy()
        else:
            if e == "sales":
                query_filter = {"sale_currency": {"$in": ["ETH", "WETH"]}}
            else:
                query_filter = {}
            df = read_mongo(
                collection=f"{collection}_{e}",
                query_projection=projection,
                query_filter=query_filter,
                return_df=True,
            )
        all = all.append(df)

    # sort by date
    all = all.sort_values("time")
    # drop duplicates
    last_update = all.drop_duplicates(subset=["asset_id"], keep="last")
    still_listed = last_update[last_update.event_type == "created"]
    # keep only listings where listing end is in the future
    still_listed = still_listed[still_listed.listing_ending > dt.datetime.now()]

    if collection == "ape-gang-old":
        migrated_apes = read_mongo(
            "ape-gang_traits",
            query_projection={"_id": 0, "asset_id": 1},
            return_df=True,
        )
        # remove migrated apes from still listed
        still_listed = still_listed[~still_listed.asset_id.isin(migrated_apes.asset_id)]

    print(
        f"{still_listed.shape[0]} {collection}'s are currently listed, with a floor of {still_listed.listing_price.min()} ETH"
    )

    # write still listed to database
    write_mongo(
        collection=f"{collection}_still_listed",
        # mongo doesn't seem to like timedelta
        data=still_listed.drop(columns=["duration"]),
        overwrite=True,
    )

    # Now update collection_floor stats

    if f"{collection}_floor_stats" in db_collections:
        # floor stats already exists for this collection
        last_updated_floor = read_mongo(
            f"{collection}_floor_stats",
            query_projection=["date"],
            query_sort=[("date", -1)],
            query_limit=1,
            return_df=True,
        )
        t0 = last_updated_floor.date[0] + dt.timedelta(days=1)
        print("should get lastUpdate from collection floor stats")
    else:
        # set t0 to when first sale was made
        sales = all[all.event_type == "successful"]
        t0 = sales.time.min()
    # how many days since last update (t0)??
    last_n_days = (dt.datetime.now() - t0).days
    # days to calculate floor stats on
    days = [t0.date() + dt.timedelta(days=i) for i in range(last_n_days + 1)]
    all["date"] = all["time"].dt.date
    # how many assets in this collection
    collection_n = count_documents(f"{collection}_traits")
    # work out
    floor_stats = pd.DataFrame()
    for d in days:
        print(f"calculate floor stats for {collection} on {d}")
        before_date = all[all["date"] <= d]
        # we want to compare listing price to sales prices
        # so calculate current average sale price on this day
        sales_before_date = before_date[before_date.event_type == "successful"]
        last_x_sales = -150
        if 51 <= sales_before_date.shape[0] <= 151:
            last_x_sales = -30
        elif sales_before_date.shape[0] < 31:
            # if under 51 sales, don't calculate floor stats on this day
            continue
        current_median_ETH = sales_before_date.sale_price.iloc[last_x_sales:-1].median()
        # work out what is listed on each day
        recent_update = before_date.drop_duplicates(subset=["asset_id"], keep="last")
        listed_today = recent_update[recent_update.event_type == "created"]
        # ensure listing ending is in future
        listed_today = listed_today[listed_today.listing_ending.dt.date >= d]
        # extract listing prices (p)
        p = listed_today.listing_price

        listed_today["listing_group"] = pd.cut(
            p,
            bins=[
                0,
                current_median_ETH * 2,
                current_median_ETH * 5,
                current_median_ETH * 10,
                p.max(),
            ],
            labels=["<2x median", "2-5x median", "5-10x median", ">10x median"],
        )
        listing_perc = (listed_today["listing_group"].value_counts() / len(p)) * 100

        x = {
            "date": dt.datetime(d.year, d.month, d.day),
            "collection": collection,
            "median_sale_ETH": current_median_ETH,
            "perc_listed": (len(p) / collection_n) * 100,
            "floor_ETH": p.min(),
            "percentile_2_ETH": p.quantile(0.01),
            "median_listing_ETH": p.median(),
            "percentile_80_ETH": p.quantile(0.8),
            "perc_listings_under_2x": listing_perc["<2x median"],
            "perc_listings_2-5x": listing_perc["2-5x median"],
            "perc_listings_5-10x": listing_perc["5-10x median"],
            "perc_listings_over_10x": listing_perc[">10x median"],
        }

        floor_stats = floor_stats.append(x, ignore_index=True)

    write_mongo(
        collection=f"{collection}_floor_stats", data=floor_stats, overwrite=False
    )
