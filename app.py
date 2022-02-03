import uvicorn
from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi import FastAPI
from ML.AgeGang_ML import update_ApeGang_pred_price
from ML.ApeGang_best_value import calc_best_apegang_listing
from fastapi_utils.tasks import repeat_every
from fastapi.encoders import jsonable_encoder

import dash
from dash import dcc, html
import dash_bootstrap_components as dbc

from createdash import create_app

app = FastAPI()
dash_app = create_app()

app.mount("/dash", WSGIMiddleware(dash_app.server))
import sys

# adding Folder_2 to the system path
sys.path.insert(0, "./opensea")

from current_listings import update_current_listings
from database import read_mongo

# set app title
app.title = "mvh.eth"

# server.config.from_object(cfg)


@app.on_event("startup")
@repeat_every(seconds=60 * 60 * 6)  # repeat every 6 hours
def update_price_pred():
    print("updating ApeGang Predicted price")
    update_ApeGang_pred_price()


@app.on_event("startup")
@repeat_every(seconds=60 * 5)  # repeat 5 mins
def update_events():
    nfts = ["ape-gang", "ape-gang-old", "boredapeyachtclub", "toucan-gang"]
    for x in nfts:
        print(f"updating {x} events")
        update_opensea_events(collection=x)
    print("update apegang best listings")
    calc_best_apegang_listing(update_listings=False)


@app.get("/")
async def root():
    return {"message": "#HODL #WAGMI"}


@app.get("/Welcome/")
def welcome_message(name: str):
    return {"message": f"Welcome {name}, #WAGMI"}


@app.get("/ApeGang USD price pred/")
async def ape_id_query(ape_id: int):
    ApeGang_USD = read_mongo(
        "ape-gang-USD-value",
        query_filter={"asset_id": ape_id},
        query_projection=["pred_USD", "pred_USD_price_diff"],
    )
    return ApeGang_USD[0]


@app.get("/ApeGang-best-value-listings/")
async def AG_best_listings(n_top_results: int):
    x = read_mongo(
        collection="ape-gang_bestvalue_opensea_listings",
        query_limit=n_top_results,
        return_df=True,
    )
    x = x.fillna("").to_dict(orient="records")

    return jsonable_encoder(x)


def query_builder(query_filter, query_projection, query_sort, query_limit):
    return {
        "filter": query_filter,
        "projection": query_projection,
        "sort": query_sort,
        "limit": query_limit,
    }


@app.get("/ApeGang-Sales/")
async def AG_sales(sale_min: float, n_top_results: int):
    AG_query = {
        "sale_price": {"$gte": sale_min},
        "sale_currency": {"$in": ["ETH", "WETH"]},
    }

    AG_old = read_mongo(
        "ape-gang-old_sales",
        query_filter=AG_query,
        return_df=True,
        query_limit=n_top_results,
        query_sort=[("time", -1)],
    )
    AG_new = read_mongo(
        "ape-gang_sales",
        query_filter=AG_query,
        return_df=True,
        query_limit=n_top_results,
        query_sort=[("time", -1)],
    )
    AG_sales = (
        AG_old.append(AG_new)
        .sort_values("time", ascending=False)
        .fillna("")
        .head(n_top_results)
        .to_dict(orient="records")
    )

    return jsonable_encoder(AG_sales)


@app.get("/Toucan-Sales/")
async def Toucan_sales(sale_min: float, n_top_results: int):
    query = {
        "sale_price": {"$gte": sale_min},
        "sale_currency": {"$in": ["ETH", "WETH"]},
    }

    toucans = read_mongo(
        "toucan-gang_sales",
        query_filter=query,
        return_df=True,
        query_limit=n_top_results,
        query_sort=[("time", -1)],
    )
    x = (
        toucans.sort_values("time", ascending=False)
        .fillna("")
        .to_dict(orient="records")
    )

    return jsonable_encoder(x)


@app.get("/BAYC-Sales/")
async def BAYC_sales(sale_min: float, n_top_results: int):
    query = {
        "sale_price": {"$gte": sale_min},
        "sale_currency": {"$in": ["ETH", "WETH"]},
    }

    BAYC = read_mongo(
        "boredapeyachtclub_sales",
        query_filter=query,
        return_df=True,
        query_limit=n_top_results,
        query_sort=[("time", -1)],
    )
    x = BAYC.sort_values("time", ascending=False).fillna("").to_dict(orient="records")

    return jsonable_encoder(x)


# create an endpoint to get sales for a given collection
@app.get("/sales/{collection}")
async def sales(collection: str, sale_min: float, n_top_results: int):
    query = {
        "sale_price": {"$gte": sale_min},
        "sale_currency": {"$in": ["ETH", "WETH"]},
    }

    sales = read_mongo(
        f"{collection}_sales",
        query_filter=query,
        return_df=True,
        query_limit=n_top_results,
        query_sort=[("time", -1)],
    )
    x = sales.sort_values("time", ascending=False).fillna("").to_dict(orient="records")

    return jsonable_encoder(x)
