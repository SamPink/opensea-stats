# # Load Libraries
import pandas as pd
import numpy as np
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt
import datetime as dt

from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestRegressor
from sklearn import svm
from sklearn.metrics import mean_absolute_error


import plotly.express as px

import os, sys

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)


from opensea.database import read_mongo, write_mongo
from opensea.cryto_prices import update_eth_usd
from opensea.current_listings import update_current_listings


def calc_current_ApeGang_median_price(last_n_sales=100):

    mongo_projection = {"_id": 0, "asset_id": 1, "sale_price": 1, "time": 1}

    new = read_mongo(
        "ape-gang_sales",
        query_projection=mongo_projection,
        query_sort=[("time", -1)],
        query_limit=last_n_sales,
        return_df=True,
    )
    old = new = read_mongo(
        "ape-gang-old_sales",
        query_projection=mongo_projection,
        query_sort=[("time", -1)],
        query_limit=last_n_sales,
        return_df=True,
    )

    sales = new.append(old).sort_values("time").iloc[-last_n_sales:, :]
    sales["sale_min"] = sales["time"].dt.floor("min")
    ETH_USD = read_mongo(
        "eth-usd",
        return_df=True,
        query_filter={"time": {"$in": sales.sale_min.to_list()}},
    )
    sales = sales.merge(ETH_USD, how="left", left_on="sale_min", right_on="time")
    sales["usd_price"] = sales["sale_price"] * sales["eth-usd-rate"]
    USD_average = (
        sales["usd_price"].rolling(last_n_sales, min_periods=1).median().iloc[-1]
    )
    return USD_average


# define function for ML preprocessing
def preprocess_ApeGang(ape_ids=[], return_sales=True, update_events=True):
    if not isinstance(ape_ids, list):
        query_filter = {"asset_id": {"$in": [ape_ids]}}
    elif isinstance(ape_ids, list) and len(ape_ids) > 0:
        query_filter = {"asset_id": {"$in": ape_ids}}
    else:
        query_filter = {}

    # load the apes

    trait_list = ["Clothes", "Ears", "Hat", "Fur", "Mouth", "Eyes"]

    # load data from MongoDB
    fields = [
        "asset_id",
        "trait_n",
        "trait_",
        "trait_n_rarity",
        "factoral_rarity",
        "rarity_rank",
    ] + trait_list
    apes = read_mongo(
        "ape-gang-old_traits",
        return_df=True,
        query_projection=fields,
        query_filter=query_filter,
    )

    df = pd.get_dummies(
        apes,
        columns=["Clothes", "Ears", "Hat", "Fur", "Mouth", "Eyes"],
    )

    if return_sales:
        # update apegang events
        if update_events:
            update_current_listings("ape-gang")
            update_current_listings("ape-gang-old")

        # Read in apegang sales data
        mongo_projection = {"_id": 0, "asset_id": 1, "sale_price": 1, "time": 1}
        sales_new = read_mongo(
            "ape-gang_sales",
            query_projection=mongo_projection,
            query_filter={"time": {"$gte": dt.datetime(2021, 8, 20)}},
            return_df=True,
        )
        sales_old = read_mongo(
            "ape-gang-old_sales",
            query_projection=mongo_projection,
            query_filter={"time": {"$gte": dt.datetime(2021, 8, 20)}},
            return_df=True,
        )
        sales = sales_new.append(sales_old).sort_values("time")

        # remove very low sales - likely transfers
        sales = sales[sales["sale_price"] > 0.05]
        # extract hour that sale occured in
        sales["sale_min"] = sales["time"].dt.floor("min")
        sales = sales.drop(columns="time")

        # calculate USD price of sale
        # update ETH_USD, then read in the data
        latest_ETH_update = read_mongo(
            "eth-usd",
            return_df=True,
            query_sort=[("time", -1)],
            query_limit=1,
            query_projection=["time"],
        )
        if sales.sale_min.max().to_pydatetime() > latest_ETH_update.time.iloc[0]:
            update_eth_usd()
        ETH_USD = read_mongo(
            "eth-usd",
            return_df=True,
            query_filter={"time": {"$in": sales.sale_min.to_list()}},
        )
        sales = sales.merge(ETH_USD, how="left", left_on="sale_min", right_on="time")
        sales["sale-USD"] = sales["sale_price"] * sales["eth-usd-rate"]

        # calculate apegang rolling average sale price
        sales = sales.sort_values("sale_min").reset_index()
        rolling_average_USD = (
            sales["sale-USD"].rolling(window=100, center=True).median()
        )
        # first 50 sales are NA - so replace with expanding median
        rolling_average_USD.iloc[0:50] = (
            sales["sale-USD"].iloc[0:50].expanding().median()
        )
        # last 50 sales will also be NA, as we used centre = TRUE
        # so recalculate with centre = FALSE
        rolling_average_USD.iloc[-49:] = (
            sales["sale-USD"].iloc[-200:].rolling(100, center=False).median().iloc[-49:]
        )

        sales["rolling_average_USD"] = rolling_average_USD

        # calculate difference from median daily sale price of all sales
        sales["price_diff_USD"] = sales["sale-USD"] - sales["rolling_average_USD"]
        sales

        # most expensive sales by price diff
        sales.sort_values("price_diff_USD", ascending=False).head(10)

        # remove low sales under 35% of rolling average
        perc_rolling_ave = sales["sale-USD"] / sales["rolling_average_USD"]
        sales = sales[perc_rolling_ave > 0.4]

        df2 = df.merge(sales[["asset_id", "price_diff_USD"]], on="asset_id")
        return df2
    else:
        return df


def train_ApeGangML(
    num_cols=["trait_n", "trait_n_rarity", "factoral_rarity", "rarity_rank"],
    test_split=0.15,
    n_trees=1000,
    rf_max_depth=13,
    rf_max_features=0.25,
    update_opensea_events=True,
):

    # preprocess categorical data
    ml_input = preprocess_ApeGang(update_events=update_opensea_events)
    # scale numeric data
    scaler = StandardScaler()
    scaler.fit(ml_input[num_cols])
    ml_input[num_cols] = scaler.transform(ml_input[num_cols])

    # make train-test splits
    X = ml_input.drop(columns=["asset_id", "price_diff_USD"])
    y = ml_input["price_diff_USD"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_split, random_state=42
    )

    # fit random forest model
    rf_reg = RandomForestRegressor(
        max_depth=rf_max_depth,
        max_features=rf_max_features,
        min_samples_split=10,
    )
    rf = GridSearchCV(
        rf_reg,
        param_grid={
            "n_estimators": [n_trees, 100],
            "max_features": [rf_max_features, "auto"],
        },
        n_jobs=-1,
        cv=10,
    )
    rf.fit(X_train, y_train)

    # predict y-values
    y_pred = rf.predict(X_test)
    # evaluate predictions
    mae = mean_absolute_error(y_test, y_pred)

    print("----------------------------------------------------")
    print(
        f"ApeGang random forest price prediction was trained on {X_train.shape[0]} sales, achieving a mean absolute error of US$={mae:.2f}"
    )
    print("----------------------------------------------------")

    # Now predict Price diff for every ape
    df = preprocess_ApeGang(return_sales=False, update_events=False)
    rarity_rank = df.copy()[["asset_id", "rarity_rank"]]
    df[num_cols] = scaler.transform(df[num_cols])

    # predict price_diff
    pred_price_diff = rf.predict(df[X_train.columns])
    average_USD = calc_current_ApeGang_median_price()
    pred_USD = pd.DataFrame(data=pred_price_diff, columns=["pred_USD_price_diff"])
    pred_USD["asset_id"] = df["asset_id"]

    # calculate USD price
    pred_USD["pred_USD"] = average_USD + pred_USD["pred_USD_price_diff"]
    pred_USD = pred_USD.sort_values("pred_USD", ascending=False)
    pred_USD["price_rank"] = np.arange(1, pred_USD.shape[0] + 1)
    pred_USD = pred_USD.merge(rarity_rank, how="left", on="asset_id")

    # write to mongo
    write_mongo("ape-gang-USD-value", pred_USD, overwrite=True)

    return rf


def update_ApeGang_pred_price():

    price_diff_df = read_mongo(
        "ape-gang-USD-value",
        query_projection=[
            "asset_id",
            "pred_USD_price_diff",
            "price_rank",
            "rarity_rank",
        ],
        return_df=True,
    )

    average_USD = calc_current_ApeGang_median_price()

    price_diff_df["pred_USD"] = average_USD + price_diff_df["pred_USD_price_diff"]
    write_mongo("ape-gang-USD-value", price_diff_df, overwrite=True)

    return price_diff_df
