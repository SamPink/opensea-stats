import pickle as pkl
import os
import sys
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
import xgboost as xgb
import requests
from sklearn.model_selection import GridSearchCV
from scipy.stats import pearsonr


currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from opensea.cryto_prices import update_eth_usd
from opensea.opensea_assets import get_opensea_metadata
from opensea.database import *
from opensea.current_listings import *


def extract_feature_names(model):
    # is model of GridSearchCV type?
    if isinstance(model, GridSearchCV):
        model = model.best_estimator_

    ## is model of xgb.XGBRegressor type extract feature names
    if isinstance(model, xgb.XGBRegressor):
        features = model.get_booster().feature_names

    ##check if model is RandomForestRegressor and extract feature names
    elif isinstance(model, RandomForestRegressor) or isinstance(
        model, GradientBoostingRegressor
    ):
        features = model.feature_names_in_

    else:
        print(f"Model type not supported: {type(model)}")
        return None

    return features


# define function to re-predicted USD value of a given collection from pkl model
def pred_USD_from_pkl(collection):
    #### read in pkl file for model and scaler
    pkl_dir = f"ML_models/{collection}/{collection}"
    with open(f"{pkl_dir}_price_pred_model.pkl", "rb") as f:
        model = pkl.load(f)

    with open(f"{pkl_dir}_scaler.pkl", "rb") as f:
        scaler = pkl.load(f)

    # get feature names from GridSearchCV model
    feature_names = extract_feature_names(model)

    ### get most 100 most recent sales with read_mongo()
    most_recent_sales = read_mongo(
        f"{collection}_sales",
        query_limit=100,
        query_projection=["asset_id", "time", "sale_price"],
        query_sort=[("time", -1)],
        return_df=True,
    )

    # get eth to usd rate from an external api
    # https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd

    eth_price_url = (
        "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
    )
    data = requests.get(eth_price_url).json()
    current_eth_price = data["ethereum"]["usd"]
    # calculate last 100 median sale price in USD
    median_sale_eth = most_recent_sales.sale_price.median()
    median_sale_usd = median_sale_eth * current_eth_price
    # print eth and usd sale price for collection
    print(
        f"Median sale price for {collection} is {median_sale_eth} (${median_sale_usd})"
    )

    ###get collection metadata
    metadata = get_opensea_metadata(collection=collection)
    trait_list = list(metadata["collection"]["traits"].keys())
    ### get traits data
    traits = read_mongo(f"{collection}_traits", return_df=True)
    # get rarity columns
    rarity_cols = [x + "_rarity" for x in trait_list]
    # calculate factoral rarity
    factorial_rarity = 1 / traits[rarity_cols]
    # calculate total rarity
    traits["factoral_rarity"] = factorial_rarity.sum(axis=1)
    traits = traits.sort_values("factoral_rarity", ascending=False)
    traits["rarity_rank"] = np.arange(1, traits.shape[0] + 1, 1)
    # calculate min rarity across rarity columns
    traits["min_rarity"] = traits[rarity_cols].min(axis=1)

    # work out which cols are numeric
    num_cols = np.intersect1d(traits.columns, feature_names)
    num_cols = np.append(num_cols, "rolling_ave_USD")

    ## extract overlap between arrays using numpy
    df = pd.get_dummies(traits, columns=trait_list + ["trait_n"])

    df["rolling_ave_USD"] = median_sale_usd
    # scale num_cols within df
    df[num_cols] = scaler.transform(df[num_cols])

    # creare predict_df with features in same order, as was originally trained in model
    predict_df = df.loc[:, feature_names]

    ###now predict USD from model
    prediction = model.predict(predict_df)

    df["predicted_USD"] = prediction
    df["prediction_time"] = pd.Timestamp.now()

    # calculate max predicted ETH

    print(
        f"Re-trained {collection}, floor = ${np.min(prediction):.2f}, median = ${np.median(prediction):.2f} and highest price = ${np.max(prediction):.2f}"
    )

    # merge predictions to traits

    df2write = df[["asset_id", "predicted_USD", "prediction_time"]].merge(
        traits, how="left", on="asset_id"
    )

    corr = pearsonr(df2write["predicted_USD"], df2write["factoral_rarity"])

    print(f"Pearson correlation between predicted USD and rarity: {corr[0]:.2f}")
    # write to mongo
    write_mongo(collection=f"{collection}_predicted_USD", data=df2write, overwrite=True)


pred_USD_from_pkl("bored-ape-kennel-club")
pred_USD_from_pkl("mfers")
pred_USD_from_pkl("supducks")
pred_USD_from_pkl("gutterdogs")
pred_USD_from_pkl("cryptomories")
