import opensea.database as db
import pandas as pd
import numpy as np
from opensea.opensea_events import *
from opensea.opensea_collections import all_collections_with_traits


collection = "boredapeyachtclub"
min_gap_seconds = 60**2


def calc_event_timediff(collection=collection, eventType="sales", min_gap_seconds=3600):
    x = (
        db.read_mongo(
            collection=f"{collection}_{eventType}",
            query_projection=["time", "asset_id"],
            return_df=True,
        )
        .drop_duplicates()
        .sort_values(by=["time"])
        .reset_index()
    )
    x["week_year"] = x["time"].dt.week.astype(str) + "_" + x["time"].dt.year.astype(str)
    x["time_diff"] = (x["time"] - x["time"].shift(1)).dt.total_seconds()
    time_diff_95_perc = x.groupby("week_year").quantile(0.99)["time_diff"]
    x = x.merge(time_diff_95_perc, on="week_year", how="left").dropna()
    x = x.rename(
        columns={"time_diff_x": "time_diff", "time_diff_y": "time_diff_99_perc"}
    )
    big_gaps = x[x.time_diff > x.time_diff_99_perc]

    return big_gaps[["time", "time_diff"]], big_gaps.time_diff.to_list()


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


def fill_event_gaps(collection=collection, min_gap_seconds=3600, eventType="sales"):
    # calculate time diffference between listings
    eventType_dict = {
        "sales": "successful",
        "transfers": "transfer",
        "listings": "created",
        "cancellations": "cancelled",
    }
    if eventType not in eventType_dict.keys():
        print(
            f"{eventType} is not a valid eventType, please try; {eventType_dict.keys()}"
        )
    x, biggest_gaps = calc_event_timediff(
        collection=collection, eventType=eventType, min_gap_seconds=min_gap_seconds
    )

    print(
        f"{len(biggest_gaps)} gaps found in {collection}_{eventType} larger than {min_gap_seconds} seconds"
    )
    new_events = []

    # fill gaps
    for time_gap in biggest_gaps:
        print(f"Time gap = {time_gap} seconds")

        gap_index = int(np.where(x["time_diff"] == time_gap)[0])
        df = x.iloc[
            [gap_index - 1, gap_index],
        ]

        before_gap = sec_since_epoch(df.time.iloc[0]) + 60
        after_gap = sec_since_epoch(df.time.iloc[1]) - 60

        i = 0
        print("-----------------------------------------------------------")
        print(f"Getting {collection} {eventType} data...")

        while True:
            events = get_opensea_events(
                collection=collection,
                search_after=before_gap,
                search_before=after_gap,
                eventType=eventType_dict[eventType],
                offset=i,
            )

            if events is not None and len(events["asset_events"]) > 0:
                i += 1  # add 1 to offsetting variable with each loop
                print(f"{i} API calls made for {collection} {eventType}")
                for event_dict in events["asset_events"]:
                    event_class = dict_to_events_class(event_dict, eventType=eventType)
                    if event_class is not None:
                        new_events.append(dict(event_class))
            else:
                break
        print(f"{len(new_events)} {eventType} found.")

    write_mongo(
        collection=f"{collection}_{eventType}",
        data=new_events,
        overwrite=False,
    )


for c in all_collections_with_traits():
    for e in ["listings", "sales", "cancellations", "transfers"]:
        fill_event_gaps(collection=c, eventType=e, min_gap_seconds=60 * 60 * 2)
