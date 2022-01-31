import config as cfg

import dash

import sys

# adding Folder_2 to the system path
sys.path.insert(0, "./opensea")
sys.path.insert(0, "./ML")

# import dash_auth
import dash_bootstrap_components as dbc

from flask import request, jsonify

from AgeGang_ML import update_ApeGang_pred_price
from ApeGang_best_value import calc_best_apegang_listing
from fastapi_utils.tasks import repeat_every
from fastapi.encoders import jsonable_encoder


from database import read_mongo
from opensea_events import *
from current_listings import update_current_listings

app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

# set app title
app.title = "mvh.eth"

server = app.server

server.config.from_object(cfg)


@server.route("/api/sales/<collection>")
def AG_sales(collection, n_top_results=10, sale_min=0):
    query = {
        "sale_price": {"$gte": sale_min},
        "sale_currency": {"$in": ["ETH", "WETH"]},
    }

    if collection == "ape-gang":
        AG_old = read_mongo(
            "ape-gang-old_sales",
            query_filter=query,
            return_df=True,
            query_limit=n_top_results,
            query_sort=[("time", -1)],
        )
        AG_new = read_mongo(
            "ape-gang_sales",
            query_filter=query,
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

        return jsonify(AG_sales)

    sales = read_mongo(
        collection=f"{collection}_sales",
        query_filter=query,
        return_df=True,
        query_limit=n_top_results,
        query_sort=[("time", -1)],
    )
    x = sales.sort_values("time", ascending=False).fillna("").to_dict(orient="records")

    return jsonify(x)
