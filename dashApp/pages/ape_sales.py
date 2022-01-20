import dash
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd

from dash import Dash, dcc, html, Input, Output, callback

import sys

sys.path.insert(0, "./opensea")

from database import read_mongo

dropdown_options = ["time", "price", "rarity"]

# make a dropdown with the options
dropdown = dcc.Dropdown(
    id="dropdown",
    options=[{"label": i, "value": i} for i in dropdown_options],
    value="time",
    style={"width": "50%"},
)

layout = html.Div(
    [
        html.H1("Hello World"),
        html.H2(id="title"),
        dropdown,
        html.Div(
            id="rows",
        ),
    ]
)


# make a callback for dropdown
@callback(
    [Output("rows", "children")],
    [Input("dropdown", "value")],
)
def update_output(value):
    if value == "price":
        query_sort = [("sale_price", -1)]
    elif value == "time":
        query_sort = [("time", -1)]
    else:
        query_sort = [("time", -1)]

    projection = {
        "_id": 0,
        "asset_id": 1,
        "image_url": 1,
        "sale_price": 1,
        "buyer_wallet": 1,
        "time": 1,
    }
    apes = read_mongo(
        "ape-gang_sales",
        return_df=True,
        query_projection=projection,
        query_limit=10,
        query_sort=query_sort,
    )
    apes_old = read_mongo(
        "ape-gang-old_sales",
        return_df=True,
        query_projection=projection,
        query_limit=10,
        query_sort=query_sort,
    )
    apes = apes.append(apes_old)

    # it seems read mongo cant filter on a list, why it do dis?
    ape_ids = apes.asset_id.unique().tolist()

    apes_rarity = read_mongo(
        "ape-gang-old_traits",
        return_df=True,
        query_filter={"asset_id": {"$in": ape_ids}},
    )

    ApeGang_USD = read_mongo(
        "ape-gang-USD-value",
        query_projection=["asset_id", "pred_USD", "pred_USD_price_diff"],
        return_df=True,
    )

    # join Apes and ApeGang_USD
    apes = apes.merge(ApeGang_USD, on="asset_id")

    # join apes_rarity to apes
    apes = apes.merge(apes_rarity, on="asset_id")

    if value == "rarity":
        apes = apes.sort_values(by=["rarity_rank"])
    elif value == "time":
        # sort by time
        apes = apes.sort_values(by=["time"], ascending=False)
    else:
        apes = apes.sort_values(by=["sale_price"], ascending=False)

    return ape_grid(apes)


def ape_grid(apes):
    return [ape_card(apes.iloc[[0]])]
    #return dbc.Row([ape_card(apes.iloc[[i]]) for i in range(apes.shape[0])])


def ape_card(ape):
    return dbc.Card(
        [
            dbc.CardImg(
                src=ape.image_url.item(),
                top=True,
            ),
            dbc.CardBody(
                [
                    html.H4(f"Ape {ape.asset_id.item()}"),
                    html.P(f"Sale Price ETH: {ape.sale_price.item()}"),
                    html.P(f"predicted diff USD: {ape.pred_USD_price_diff.item()}"),
                    html.P(f"Buyer: {ape.buyer_wallet.item()}"),
                    html.P(f"Rarity {ape.rarity_rank.item()}"),
                ]
            ),
        ],
        style={"width": "18rem"},
    )
