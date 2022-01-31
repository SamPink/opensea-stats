import dash
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output, callback
import pandas as pd
import sys

sys.path.insert(0, "./opensea")

from database import read_mongo


""" if value == "price":
        query_sort = [("sale_price", -1)]
    elif value == "time":
        query_sort = [("time", -1)]
    else:
        query_sort = [("time", -1)] """


def page_best_listings():

    df = read_mongo(
        collection="ape-gang_bestvalue_opensea_listings",
        query_limit=30,
        return_df=True,
    )

    # get asset ids
    ape_ids = df["asset_id"].tolist()

    apes_rarity = read_mongo(
        f"ape-gang-old_traits",
        return_df=True,
        query_filter={"asset_id": {"$in": ape_ids}},
    )

    # join rarity to df
    df = df.merge(apes_rarity, on="asset_id", how="left")

    # return html.Div([ape_card(df.iloc[[0]])])
    return html.Div(
        [
            html.H1("Hello World"),
            html.H2(id="title"),
            html.Div(
                dbc.Row([ape_card_listing(df.iloc[[i]]) for i in range(df.shape[0])])
            ),
        ]
    )


def ape_card_listing(ape):
    print(ape.info())
    return dbc.Card(
        [
            dbc.CardImg(
                src=ape.image_url.item(),
                top=True,
            ),
            dbc.CardBody(
                [
                    html.H4(f"Ape {ape.asset_id.item()}"),
                    html.P(f"Listing Price: {ape.listing_USD.item()}"),
                    html.P(f"predicted price: {ape.pred_USD.item()}"),
                    html.P(f"Rarity: {ape.rarity_rank_y.item()}"),
                ]
            ),
        ],
        style={"width": "18rem"},
    )
