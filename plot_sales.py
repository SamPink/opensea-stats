from opensea.database import *
import datetime as dt
from opensea.opensea_events import *
import plotly.express as px


collection = "mutant-ape-yacht-club"


def plot_sales(collection, last_n_days=120, rolling_n=200):
    update_opensea_events(collection, eventTypes=["sales"])

    t0 = dt.datetime.now() - dt.timedelta(days=last_n_days)
    sales = (
        read_mongo(
            f"{collection}_sales",
            query_filter={"time": {"$gte": t0}, "sale_price": {"$gt": 0}},
            return_df=True,
        )
        .drop_duplicates()
        .sort_values("time", ascending=True)
    )

    sales["median"] = sales.sale_price.rolling(rolling_n).median()
    sales["percentile_80th"] = sales.sale_price.rolling(rolling_n).quantile(0.8)
    sales["percentile_5th"] = sales.sale_price.rolling(rolling_n).quantile(0.05)

    df = pd.melt(
        sales,
        id_vars=["time"],
        value_vars=["median", "percentile_80th", "percentile_5th"],
        var_name=f"rolling_{rolling_n}sale_stats",
        value_name="ETH",
    )

    fig = px.line(
        df,
        x="time",
        y="ETH",
        color=f"rolling_{rolling_n}sale_stats",
        title=f"{collection} sales",
    )
    return fig.show()


# plot_sales("world-of-women-nft", rolling_n=300)
# plot_sales("mfers", rolling_n=250, last_n_days=40)


def plot_floor_depth(collection, last_n_days=120):
    update_opensea_events(collection)
    all = pd.DataFrame()  # define empty dataframe
    event_types = ["sales", "listings", "cancellations", "transfers"]
    projection = ["time", "event_type", "asset_id", "sale_price"]
    proj_listings = ["listing_price", "duration"] + projection
    for e in event_types:
        ## get all info for listings - that are dutch and public
        if e == "listings":
            listings = read_mongo(
                collection=f"{collection}_{e}",
                query_projection=proj_listings,
                query_filter={"private_auction": False, "auction_type": "dutch"},
                return_df=True,
            ).drop_duplicates()
            # very long listings can screw with addition
            # set anything over 5 years to 5years
            five_yr_in_sec = 1.578e8
            listings.loc[
                listings["duration"] > five_yr_in_sec, "duration"
            ] = five_yr_in_sec
            listings["duration"] = pd.to_timedelta(listings["duration"], "s")

            listings["listing_ending"] = listings["time"] + listings["duration"]
            df = listings.copy()
        else:
            df = read_mongo(
                collection=f"{collection}_{e}",
                query_projection=projection,
                return_df=True,
            ).drop_duplicates()
        all = all.append(df)
    all = all.sort_values("time")

    t0 = dt.datetime.now() - dt.timedelta(days=last_n_days)
    # if t0 is before first datapoint, choose date from first datapoint
    if max([t0, listings.time.min()]) == listings.time.min():
        t0 = listings.time.min()
        last_n_days = (dt.datetime.now() - t0).days
    days = [t0.date() + dt.timedelta(days=i) for i in range(last_n_days + 1)]
    all["date"] = all["time"].dt.date
    n_listings = pd.DataFrame()

    for d in days:
        before_date = all[all["date"] <= d]
        current_median_ETH = (
            before_date[before_date.event_type == "successful"]
            .sale_price.iloc[-100:-1]
            .median()
        )
        last_update = before_date.drop_duplicates(subset=["asset_id"], keep="last")
        still_listed = last_update[last_update.event_type == "created"]
        still_listed = still_listed[still_listed.listing_ending.dt.date >= d]
        p = still_listed.listing_price
        still_listed["listing_group"] = pd.cut(
            p,
            bins=[
                p.min(),
                current_median_ETH * 2,
                current_median_ETH * 5,
                current_median_ETH * 10,
                p.max(),
            ],
            labels=["<2x median", "2-5x median", "5-10x median", ">10x median"],
        )
        x = (
            still_listed.groupby("listing_group")
            .count()
            .rename(columns={"asset_id": "n_listings"})["n_listings"]
            .reset_index()
        )
        x["date"] = d
        n_listings = n_listings.append(x)

    # work out number of listings as percentage of collection
    collection_n = count_documents(f"{collection}_traits")
    n_listings["listed_perc"] = 100 * (n_listings["n_listings"] / collection_n)
    # plot figure
    fig = px.bar(
        n_listings,
        x="date",
        y="listed_perc",
        color="listing_group",
        labels={"listed_perc": "Listed %"},
    )
    fig.update_layout(
        font={"size": 16},
        title={"text": f"<b>{collection} listings over time</b>", "font": {"size": 30}},
    )

    fig.show()


collections = ["cryptomories"]
for i in collections:
    plot_floor_depth(i, last_n_days=100)
    plot_sales(i, rolling_n=100, last_n_days=100)
