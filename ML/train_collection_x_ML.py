# # Load Libraries

from xgboost import XGBRegressor
from sklearn.svm import SVR
from sklearn.linear_model import LinearRegression, SGDRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import explained_variance_score, mean_absolute_error
import plotly.express as px
import pickle as pkl
import datetime as dt
import numpy as np
import pandas as pd
import os
import sys


currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)
from opensea.opensea_collections import all_collections_with_traits
from opensea.opensea_assets import get_opensea_metadata
from opensea.cryto_prices import update_eth_usd
from opensea.database import read_mongo, write_mongo

# Now import local modules


def collection_autoML(collection, sales_after=dt.datetime(2000, 1, 1)):

    # check we have data for inputted collection
    if collection not in all_collections_with_traits():
        print(f"{collection} is not a valid collection")
        return None
    # define projections and filters for mongoDB query
    sales_proj = ["asset_id", "time", "sale_price"]
    only_ETH = {
        "sale_currency": {"$in": ["ETH", "WETH"]},  # only keep ETH sales
        "time": {"$gte": sales_after},  # sold after inputted time
        "sale_price": {"$gt": 0},  # remove anything that sold for 0ETH
    }
    # read in sales data for collection
    sales = read_mongo(
        f"{collection}_sales",
        return_df=True,
        query_projection=sales_proj,
        query_filter=only_ETH,
    ).drop_duplicates()  # drop any duplicate sales

    if sales.shape[0] < 4000:
        print(f"{sales.shape[0]} {collection} is not enough to train model")
        return None

    if collection == "cryptopunks":
        top_legit_sale = 8500
        sales = sales[
            sales.sale_price < top_legit_sale
        ]  # remove FAKE high sales from cryptopunks

    # summarise time of sale by the hour (to calculate ETH price at that hour)
    sales["sale_hour"] = sales["time"].dt.floor("h")
    sales = sales.drop(columns="time")

    # update ETH_USD, if sale times are later tha last ETH update
    latest_ETH_update = read_mongo(
        "eth-usd",
        return_df=True,
        query_sort=[("time", -1)],
        query_limit=1,
        query_projection=["time"],
    )
    if sales.sale_hour.max().to_pydatetime() > latest_ETH_update.time.iloc[0]:
        update_eth_usd()
    ETH_USD = read_mongo(
        "eth-usd",
        return_df=True,
        query_filter={"time": {"$in": sales.sale_hour.to_list()}},
    )

    # calculate USD price at time of sale
    sales = sales.merge(ETH_USD, how="left", left_on="sale_hour", right_on="time")
    sales["sale_USD"] = sales["sale_price"] * sales["eth-usd-rate"]

    # calculate rolling median price per 100 sales
    sales = sales.sort_values("sale_hour").reset_index(drop=True)
    sales["rolling_ave_USD"] = np.nan
    sales["rolling_ave_USD"] = (
        sales["sale_USD"].rolling(window=100, center=True).median()
    )

    # first 50 sales are NA - so replace with expanding median
    sales["rolling_ave_USD"].iloc[0:50] = (
        sales["sale_USD"].iloc[0:50].expanding().median()
    )

    # last 50 sales will also be NA, as we used centre = TRUE
    # so recalculate with centre = FALSE
    sales["rolling_ave_USD"].iloc[-49:] = (
        sales["sale_USD"].iloc[-151:].rolling(100, center=False).median().iloc[-49:]
    )
    # pull out the median price for last 10
    current_USD_ave = sales.rolling_ave_USD.iloc[-1]

    sales["price_perc"] = (sales["sale_USD"] / sales["rolling_ave_USD"]) * 100
    sales = sales[sales["price_perc"] > 20]
    if sales.shape[0] < 2000:
        print(
            f"{collection} only has {sales.shape[0]} sales, not enough to build model - at least 2000 required.."
        )
        return None
    print(f"Retrieved {sales.shape[0]} {collection} sales after {sales_after}")

    # now get traits info

    metadata = get_opensea_metadata(collection=collection)
    trait_list = list(metadata["collection"]["traits"].keys())
    fields = [
        "asset_id",
        "trait_n",
        "trait_n_rarity",
        "min_rarity",
        "factoral_rarity",
        "rarity_rank",
    ] + trait_list

    rarity_cols = [x + "_rarity" for x in trait_list]

    traits = read_mongo(
        f"{collection}_traits",
        query_sort=[("rarity_rank", 1)],
        return_df=True,
    )
    # calculate min rarity
    traits["asset_id"] = pd.to_numeric(traits["asset_id"])
    traits["min_rarity"] = traits[rarity_cols].min(axis=1)
    traits_sales = traits[fields].merge(
        sales[["asset_id", "sale_USD", "rolling_ave_USD"]], on="asset_id", how="outer"
    )

    df = pd.get_dummies(
        traits_sales,
        columns=trait_list + ["trait_n"],
    )

    # scale numeric colum
    # scale numeric data
    df_scaled = df.copy()
    scaler = StandardScaler()
    num_cols = [
        "trait_n_rarity",
        "min_rarity",
        "factoral_rarity",
        "rarity_rank",
        "rolling_ave_USD",
    ]
    scaler.fit(df_scaled[num_cols])
    df_scaled[num_cols] = scaler.transform(df_scaled[num_cols])

    # make train-test splits

    with_sales = df_scaled.sale_USD.notna()

    X = df_scaled.copy().drop(columns=["asset_id", "sale_USD"])[with_sales]
    y = df_scaled.sale_USD[with_sales]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42
    )

    # get data to predict new values from
    X_predict = df.copy().drop_duplicates("asset_id").drop(columns=["sale_USD"])
    X_predict.rolling_ave_USD = current_USD_ave
    X_predict[num_cols] = scaler.transform(X_predict[num_cols])

    # train some basic models to find which algorith performs best on the data
    models = []
    MAE = []
    trained_models = []
    model_ypreds = []
    models.append(("Linear Regression", LinearRegression()))
    models.append(
        (
            "XGBoost",
            XGBRegressor(
                n_estimators=X.shape[1] * 5, max_depth=7, eta=0.1, subsample=0.7
            ),
        )
    )
    # models.append(
    #    (
    #        "Multi-layer Perceptron",
    #        MLPRegressor(max_iter=1e5, hidden_layer_sizes=(100,),early_stopping=True),validation_fraction=0.15
    #    )
    # )
    models.append(
        ("Random Forest", RandomForestRegressor(n_estimators=(X.shape[1] * 5)))
    )
    models.append(
        (
            "Random Forest - new params",
            RandomForestRegressor(
                n_estimators=(X_train.shape[1] * 8), max_depth=12, max_features=0.5
            ),
        )
    )
    models.append(("Stochastic Gradient Descent", SGDRegressor()))
    models.append(("Gradient Boosting", GradientBoostingRegressor()))
    models.append(("Support Vector Machine", SVR()))

    for name, model in models:
        model_CV = GridSearchCV(
            model, cv=10, scoring="neg_mean_absolute_error", param_grid={}, n_jobs=-1
        )
        model_CV.fit(X_train, y_train)
        CV_MAE = abs(model_CV.best_score_)
        # calculate error on the unseen test data
        y_pred = model_CV.predict(X_test)
        model_ypreds.append((collection, y_pred))
        test_mae = mean_absolute_error(y_test, y_pred)
        MAE.append(test_mae)

        # calculate predicted USD price for all assets in collection
        X_predict[f"{name}_predict"] = model_CV.predict(X_predict[X.columns])
        # save the trained model in ist
        trained_models.append(model_CV)

        # print message
        print(f"{name} Cross-validation MAE=${CV_MAE:.2f} and Test MAE =${test_mae}")
    # Hyperparamater tune the best model
    dir = f"ML/{collection}"
    if not os.path.isdir(dir):
        os.makedirs(dir)
    best_model_index = int(np.where(MAE == min(MAE))[0])
    best_model = models[best_model_index][0]
    predictions = X_predict[["asset_id", f"{best_model}_predict"]].merge(
        traits, on="asset_id"
    )
    predictions = predictions.rename(columns={f"{best_model}_predict": "predicted_USD"})
    predictions["ML_model"] = best_model

    # make figure
    best_model_ypred = model_ypreds[best_model_index][1]
    exp_var = explained_variance_score(y_pred=best_model_ypred, y_true=y_test) * 100

    fig = px.scatter(
        x=best_model_ypred,
        y=y_test,
        trendline="lowess",
        trendline_options=dict(frac=0.1),
        title=f"{collection} USD price prediction <br><sup>Mean absolute error =${MAE[best_model_index]:.2f} | Explained Variance % ={exp_var:.1f}<sup>",
        labels={
            "x": f"Predicted {collection} Sale Price (USD)",
            "y": f"Actual {collection} Sale Price (USD)",
        },
    )
    fig.write_html(f"ML/{collection}/{collection}_scatterplot.html")

    pkl.dump(
        trained_models[best_model_index],
        open(f"ML/{collection}/{collection}_price_pred_model.pkl", "wb"),
    )
    pkl.dump(scaler, open(f"ML/{collection}/{collection}_scaler.pkl", "wb"))
    write_mongo(
        data=predictions, collection=f"{collection}_predicted_USD", overwrite=True
    )
