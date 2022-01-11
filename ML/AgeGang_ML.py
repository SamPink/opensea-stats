# # Load Libraries
import pandas as pd
import numpy as np
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt

from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error


import plotly.express as px

import os, sys
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)


from opensea.database import read_mongo, write_mongo
from opensea.cryto_prices import update_eth_usd
from opensea.current_listings import update_current_listings


# update apegang events
update_current_listings("ape-gang")
update_current_listings("ape-gang-old")

# Read in apegang sales data
mongo_projection = {"_id": 0, "asset_id": 1, "sale_price": 1, "time": 1}
sales_new = read_mongo(
    "ape-gang_sales", query_projection=mongo_projection, return_df=True
)
sales_old = read_mongo(
    "ape-gang-old_sales", query_projection=mongo_projection, return_df=True
)
sales = sales_new.append(sales_old)


# remove very low sales - likely transfers
sales = sales[sales["sale_price"] > 0.05]
# extract hour that sale occured in
sales["sale_min"] = sales["time"].dt.floor("min")
sales = sales.drop(columns="time")


# calculate USD price of sale
# update ETH_USD, then read in the data
update_eth_usd()
ETH_USD = read_mongo("eth-usd", return_df=True)
sales = sales.merge(ETH_USD, how="left", left_on="sale_min", right_on="time")
sales["sale-USD"] = sales["sale_price"] * sales["eth-usd-rate"]


# calculate apegang daily median sales prices in USD
sales["day"] = sales["sale_min"].dt.date
sales_by_date = sales.groupby("day").count().sale_price
daily_median = sales.groupby(sales.day)[["sale_price", "sale-USD"]].median()


# calculate difference from median daily sale price of all sales
sales = sales.join(daily_median, rsuffix="_daily_avg", on="day")
sales["price_diff_ETH"] = sales["sale_price"] - sales["sale_price_daily_avg"]
sales["price_diff_USD"] = sales["sale-USD"] - sales["sale-USD_daily_avg"]
sales


# most expensive sales by price diff
sales.sort_values("price_diff_USD", ascending=False).head(10)


# remove low sales (sold at 1500 USD below median)
sales = sales[sales["price_diff_USD"] > -1500]


# load the apes

trait_list = ["Clothes", "Ears", "Hat", "Fur", "Mouth", "Eyes"]


# define function for ML preprocessing
def preprocess_ApeGang(ape_ids=[], return_sales=True, sales=sales):
    if not isinstance(ape_ids, list):
        query_filter = {"asset_id": {"$in": [ape_ids]}}
    elif isinstance(ape_ids, list) and len(ape_ids) > 0:
        query_filter = {"asset_id": {"$in": ape_ids}}
    else:
        query_filter = {}

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
        columns=["trait_n", "Clothes", "Ears", "Hat", "Fur", "Mouth", "Eyes"],
    )

    if return_sales:
        df2 = df.merge(sales[["asset_id", "price_diff_USD"]], on="asset_id")
        return df2
    else:
        return df


import joblib


def train_ApeGangML(
    sales=sales,
    num_cols=["trait_n_rarity", "factoral_rarity", "rarity_rank"],
    test_split=0.15,
    n_trees=1000,
    rf_max_depth=13,
    rf_max_features=0.25,
):

    # preprocess categorical data
    ml_input = preprocess_ApeGang(sales=sales)
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
    rf = RandomForestRegressor(
        max_depth=rf_max_depth,
        max_features=rf_max_features,
        min_samples_split=10,
        n_estimators=n_trees,
    )
    rf.fit(X_train, y_train)

    # save model as .joblib
    joblib.dump(rf, "ML/ApeGang_Price_pred.joblib")

    # predict y-values
    y_pred = rf.predict(X_test)
    # evaluate predictions
    mae = mean_absolute_error(y_test, y_pred)
    print("----------------------------------------------------")
    print(
        f"ApeGang random-forest price prediction was trained on {X_train.shape[0]} sales, achieving a mean absolute error of US$={mae:.2f}"
    )
    print("----------------------------------------------------")

    return rf, scaler, X_train.columns


rf, scaler, trained_vars = train_ApeGangML(test_split=0.25, n_trees=1500)


def pred_ape_price(
    ape_ids=[-1], model=rf, scaler=scaler, input_cols=trained_vars, sales_df=sales
):
    if max(ape_ids) > 10000 or min(ape_ids) < 0:
        ape_ids = []
    # obtain preprocessed df for inputted apes
    df = preprocess_ApeGang(ape_ids=ape_ids, return_sales=False)
    num_cols = ["trait_n_rarity", "factoral_rarity", "rarity_rank"]
    df[num_cols] = scaler.transform(df[num_cols])

    # predict price_diff
    pred_price_diff = model.predict(df[input_cols])
    pred_USD = pd.DataFrame(
        index=df["asset_id"], data=pred_price_diff, columns=["pred_USD_price_diff"]
    )

    # find all sales that have occured in previous 24hrs (from last registered sale)
    most_recent_sale = sales_df.time.max()
    sale_minus24hr = most_recent_sale - dt.timedelta(hours=24)

    last24hr_sales = sales[
        (sales["time"] > sale_minus24hr) & (sales["time"] < most_recent_sale)
    ]
    median_24hr_price = last24hr_sales["sale-USD_daily_avg"].median()

    # calculate USD price
    pred_USD["pred_USD"] = median_24hr_price + pred_USD["pred_USD_price_diff"]
    pred_USD = pred_USD.sort_values("pred_USD", ascending=False)
    pred_USD["asset_id"] = pred_USD.index
    return pred_USD


ape_gang_USD = pred_ape_price()

write_mongo("ape-gang-USD-value", ape_gang_USD, overwrite=True)
