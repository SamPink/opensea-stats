# # Load Libraries
import pandas as pd
import numpy as np
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt
import datetime as dt
import re
import datetime as dt
import plotly.express as px
from dateutil import parser

from xgboost import XGBRegressor
from sklearn.svm import SVR
from sklearn.linear_model import LinearRegression, SGDRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import explained_variance_score, mean_absolute_error


import os, sys


currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from opensea.database import read_mongo, write_mongo, connect_mongo
from opensea.cryto_prices import update_eth_usd
from opensea.opensea_assets import get_opensea_metadata


database = connect_mongo()
db_collections = database.collection_names(include_system_collections=False)
sales_regex = re.compile(".*_sales")
sales_collections = list(filter(sales_regex.match, db_collections))
collection_with_sales = [re.sub("_sales", "", i) for i in sales_collections]


traits_regex = re.compile(".*_traits")
traits_collections = list(filter(traits_regex.match, db_collections))
collection_with_traits = [re.sub("_traits", "", i) for i in traits_collections]


"""missing_traits = list(set(collection_with_sales) - set(collection_with_traits))
for i in missing_traits:
    get_collection_assets(i)
    time.sleep(60)
    update_opensea_events(i,eventTypes=["sales"])
    time.sleep(60)
    update_opensea_events(i,eventTypes=["sales"],
                          find_firstUpdated_from_DB=True, find_lastUpdated_from_DB=False)"""


database = connect_mongo()
db_collections2 = database.collection_names(include_system_collections=False)
traits_collections2 = list(filter(traits_regex.match, db_collections2))
collection_with_traits2 = [re.sub("_traits", "", i) for i in traits_collections2]

collections = list(
    set.intersection(set(collection_with_sales), set(collection_with_traits2))
)


sales = pd.DataFrame()
traits = pd.DataFrame()
rarity_col_regex = re.compile(".*_rarity")
for x in collections:
    metadata = get_opensea_metadata(collection=x)
    mint_time = parser.parse(metadata["collection"]["created_date"])
    print(f"getting data for {x}")
    sales_x = read_mongo(
        f"{x}_sales",
        query_projection=[
            "asset_id",
            "collection",
            "time",
            "sale_currency",
            "sale_price",
        ],
        query_filter={
            "sale_price": {"$gt": 0},
            "sale_currency": {"$in": ["ETH", "WETH"]},
        },
        return_df=True,
    ).drop_duplicates()
    sales_x["days_since_mint"] = (sales_x["time"] - mint_time).dt.total_seconds() / (
        60 * 60 * 24
    )
    sales_x["days_since_epoch"] = (
        sales_x["time"] - dt.datetime(1970, 1, 1)
    ).dt.total_seconds() / (60 * 60 * 24)
    sales = sales.append(sales_x)
    traits_x = read_mongo(f"{x}_traits", return_df=True)
    rarity_cols = list(filter(rarity_col_regex.match, traits_x.columns))
    rarity_cols.remove("factoral_rarity")
    traits_x["collection"] = x
    traits_x["mean_rarity"] = traits_x[rarity_cols].mean(axis=1)
    traits_x["min_rarity"] = traits_x[rarity_cols].min(axis=1)
    traits_x["max_rarity"] = traits_x[rarity_cols].max(axis=1)
    traits_x["factoral_rarity"] = (
        traits_x["factoral_rarity"] / traits_x["factoral_rarity"].max()
    )
    traits_x["rarity_rank"] = traits_x["rarity_rank"] / traits_x["rarity_rank"].max()
    traits_x["trait_n"] = traits_x["trait_n"] / traits_x["trait_n"].max()

    cols_2_keep = [
        "asset_id",
        "collection",
        "trait_n",
        "trait_n_rarity",
        "mean_rarity",
        "max_rarity",
        "min_rarity",
        "factoral_rarity",
        "rarity_rank",
    ]

    traits = traits.append(traits_x[cols_2_keep])


# convert price to dollars
sales["sale_hour"] = sales["time"].dt.floor("h")
sales = sales.drop(columns="time")
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


sales = sales.merge(ETH_USD, how="left", left_on="sale_hour", right_on="time")
sales["sale_USD"] = sales["sale_price"]
ETH_sale = sales.sale_currency.isin(["WETH", "ETH"])
# if sales are in ETH, convert USD price
sales.loc[ETH_sale, "sale_USD"] = (
    sales.loc[ETH_sale, "sale_price"] * sales.loc[ETH_sale, "eth-usd-rate"]
)

# make all apegang = ape-gang old
AG_new = sales.collection == "ape-gang"
sales.loc[AG_new, "collection"] = "ape-gang-old"

# remove the fake cryptopunk sale over 10K ETH
sales = sales[~((sales.collection == "cryptopunks") & (sales.sale_price > 10000))]

# calculate rolling average price per collection
sales["collection_rolling_ave_USD"] = np.nan
sales_copy = (
    sales.copy().sort_values(by=["collection", "sale_hour"]).reset_index(drop=True)
)
sales = pd.DataFrame()
last_day = pd.DataFrame()

for x in sales_copy.collection.unique():
    df = sales_copy[sales_copy.collection == x]

    df["collection_rolling_ave_USD"] = (
        df["sale_USD"].rolling(window=100, center=True).median()
    )

    # first 50 sales are NA - so replace with expanding median
    df["collection_rolling_ave_USD"].iloc[0:50] = (
        df["sale_USD"].iloc[0:50].expanding().median()
    )

    # last 50 sales will also be NA, as we used centre = TRUE
    # so recalculate with centre = FALSE
    df["collection_rolling_ave_USD"].iloc[-49:] = (
        df["sale_USD"].iloc[-151:].rolling(100, center=False).median().iloc[-49:]
    )

    df["sale_date"] = df.sale_hour.dt.date
    five_day_change = pd.DataFrame(
        df.groupby("sale_date").mean()["collection_rolling_ave_USD"]
    )
    five_day_change["back5days"] = five_day_change.collection_rolling_ave_USD.shift(5)
    five_day_change["back5days"].iloc[0:5] = five_day_change["back5days"].iloc[5]
    five_day_change["perc_change_5d"] = 100 * (
        five_day_change["collection_rolling_ave_USD"] / five_day_change["back5days"]
    )
    ATH_time = (
        df.time[df.collection_rolling_ave_USD == df.collection_rolling_ave_USD.max()]
        .iloc[0]
        .to_pydatetime()
    )
    df = df.merge(
        five_day_change[["perc_change_5d"]], left_on="sale_date", right_index=True
    )
    df["time_since_ATH"] = (df["time"] - ATH_time).dt.total_seconds() / (60 * 60 * 24)
    sales = sales.append(df)
    last_day = last_day.append(
        df[
            [
                "days_since_mint",
                "collection",
                "days_since_epoch",
                "time_since_ATH",
                "collection_rolling_ave_USD",
                "perc_change_5d",
            ]
        ].tail(1)
    )


traits["asset_id"] = pd.to_numeric(traits["asset_id"])
df = sales.merge(traits, on=["collection", "asset_id"], how="inner")
df.shape[0]

cols2keep = [
    "days_since_mint",
    "days_since_epoch",
    "time_since_ATH",
    "collection_rolling_ave_USD",
    "perc_change_5d",
    "trait_n_rarity",
    "mean_rarity",
    "max_rarity",
    "min_rarity",
    "factoral_rarity",
    "rarity_rank",
]
x = df[cols2keep]
scaler = StandardScaler()
scaler.fit(x[cols2keep])
x[cols2keep] = scaler.transform(x[cols2keep])
y = df["sale_USD"]

X_train, X_test, y_train, y_test = train_test_split(
    x, y, test_size=0.15, random_state=42
)

# train some basic models to find which algorith performs best on the data
models = []
MAE = []
Explained_Variance = []
trained_models = []
model_ypreds = []
models.append(("Linear Regression", LinearRegression()))
models.append(
    (
        "XGBoost",
        XGBRegressor(n_estimators=x.shape[1] * 5, max_depth=7, eta=0.1, subsample=0.7),
    )
)

models.append(("Random Forest", RandomForestRegressor(n_estimators=(x.shape[1] * 5))))
models.append(
    (
        "Random Forest - new params",
        RandomForestRegressor(
            n_estimators=(x.shape[1] * 8), max_depth=12, max_features=0.5
        ),
    )
)
models.append(("Stochastic Gradient Descent", SGDRegressor()))
models.append(("Gradient Boosting", GradientBoostingRegressor()))
models.append(("Support Vector Machine", SVR()))

model_CV2 = GridSearchCV(
    RandomForestRegressor(n_estimators=500, max_depth=13, max_features=0.5, n_jobs=-1),
    cv=10,
    scoring="neg_mean_absolute_error",
    param_grid={},
    n_jobs=-1,
)

model_CV2.fit(X_train.drop(columns=["perc_change_5d"]), y_train)

model2_ypred = model_CV2.predict(X_test.drop(columns=["perc_change_5d"]))
model2_mae = mean_absolute_error(y_test, model2_ypred)
expl_var = explained_variance_score(y_test, model2_ypred)


"""f
dfor name, model in models:
    model_CV = GridSearchCV(
        model, cv=10, scoring="neg_mean_absolute_error", param_grid={}, n_jobs=-1
    )
    model_CV.fit(X_train, y_train)
    CV_MAE = abs(model_CV.best_score_)
    # calculate error on the unseen test data
    y_pred = model_CV.predict(X_test)
    model_ypreds.append((name, y_pred))
    test_mae = mean_absolute_error(y_test, y_pred)
    expl_var = explained_variance_score(y_test, y_pred)
    MAE.append(test_mae)
    Explained_Variance.append(expl_var)

    # save the trained model in ist
    trained_models.append(model_CV)

    # print message
    print(
        f"{name} Cross-validation MAE=${CV_MAE:.2f}, Test MAE =${test_mae:.2f} and test explained variance ={expl_var:.3f}"
    )
    
    """

dir = "ML/All_collections"
if not os.path.isdir(dir):
    os.makedirs(dir)

best_model = model_CV2

X_predict = traits.copy().merge(last_day, on="collection", how="inner")
trained_cols = X_train.drop(columns=["perc_change_5d"]).columns
X_predict[X_train.columns] = scaler.transform(X_predict[X_train.columns])

X_predict["predicted_USD"] = best_model.predict(X_predict[trained_cols])
X_predict["ML_model"] = str(best_model.best_estimator_)

# make figure
fig = px.scatter(
    x=model2_ypred,
    y=y_test,
    opacity=0.3,
    trendline="lowess",
    trendline_options=dict(frac=0.5),
    title=f"All collection NFT USD price prediction <br><sup>Mean absolute error =${model2_mae:.2f} | Explained Variance % ={expl_var*100:.1f}<sup>",
    labels={
        "x": f"Predicted Sale Price (USD)",
        "y": f"Actual Sale Price (USD)",
    },
)
fig.write_html(f"{dir}/All_collection_scatterplot.html")

"""
model_CV = GridSearchCV(RandomForestRegressor(
        n_estimators=500, max_depth=12, max_features=0.4
    ), cv=10, scoring="neg_mean_absolute_error", param_grid={}, n_jobs=-1    )


model_CV3 = GridSearchCV(RandomForestRegressor(
        n_estimators=1500, max_depth=12, max_features=0.5, criterion='absolute_error',oob_score=True,n_jobs=-1
    ), cv=10, scoring="neg_mean_absolute_error", param_grid={}, n_jobs=-1    )
model1_mae =4421.4
model2_ypred = model_CV2.predict(X_test.drop(columns=['perc_change_5d']))
model2_mae = mean_absolute_error(y_test, model2_ypred)
model3_ypred =model_CV3.predict(X_test.drop(columns=['perc_change_5d',"days_since_mint"])
model3_mae= mean_absolute_error(y_test, model3_ypred)

RF_mae = [model1_mae,model2_mae,model3_mae]
RF_models = [model_CV,model_CV2,model_CV3]
best_model_index = int(np.where(MAE == min(MAE))[0])
print(f"Best RF model =model_CV{best_model_index+1}")
best_model = RF_models[best_model_index]
"""
import pickle as pkl

collection = "All_collections"
pkl.dump(
    best_model,
    open(f"ML/{collection}/{collection}_price_pred_model.pkl", "wb"),
)
pkl.dump(scaler, open(f"ML/{collection}/{collection}_scaler.pkl", "wb"))
write_mongo(
    data=X_predict[["asset_id", "collection", "predicted_USD", "ML_model"]],
    collection=f"{collection}_predicted_USD",
    overwrite=True,
)
