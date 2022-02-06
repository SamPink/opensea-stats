import dash
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output, callback
import pandas as pd
import sys

sys.path.insert(0, "./opensea")

from opensea.database import read_mongo


""" if value == "price":
        query_sort = [("sale_price", -1)]
    elif value == "time":
        query_sort = [("time", -1)]
    else:
        query_sort = [("time", -1)] """


def page_best_listings():

    df = read_mongo(
        collection="ape-gang_bestvalue_opensea_listings",
        query_limit=100,
        return_df=True,
    )[
        [
            "asset_id",
            "pred_USD",
            "collection",
            "listing_currency",
            "listing_price",
            "listing_ending",
            "listing_USD",
            "listing_value",
        ]
    ]

    # get asset ids
    ape_ids = df["asset_id"].tolist()

    apes_rarity = read_mongo(
        f"ape-gang-old_traits",
        return_df=True,
        query_filter={"asset_id": {"$in": ape_ids}},
    )

    # get unique number of traits

    # join rarity to df
    df = df.merge(apes_rarity, on="asset_id", how="left")

    ETH_USD = read_mongo(
        "eth-usd",
        return_df=True,
        query_sort=[("time", -1)],
        query_limit=1,
    )

    df["listing_eth"] = df.listing_USD / ETH_USD["eth-usd-rate"].item()
    df["pred_eth"] = df.pred_USD / ETH_USD["eth-usd-rate"].item()

    # return html.Div([ape_card(df.iloc[[0]])])
    return html.Div(
        [
            html.H1("Best Apes Listed"),
            dbc.Alert(
                "ETH value is currently wrong as we are converting at time of listing and ETH has gone down since then :( ",
                color="warning",
            ),
            dbc.Alert(
                "Opensea url only points to Ape Gang old currently",
                color="warning",
            ),
            html.H2(id="title"),
            html.Div(
                dbc.Row([ape_card_listing(df.iloc[[i]]) for i in range(df.shape[0])])
            ),
        ]
    )


def ape_card_listing(ape):
    if ape.collection.item() == "ape-gang-old":
        link = dbc.CardLink("Opensea listing", href=ape.permalink.item())
    else:
        link = html.P("Listed on ape gang new")

    # round pred_eth up to nearest 0.01
    pred_eth = round(ape.pred_eth.item(), 2)

    # round listing_eth up to nearest 0.01
    listing_eth = round(ape.listing_eth.item(), 2)

    return dbc.Card(
        [
            dbc.CardImg(
                src=ape.image_url.item(),
                top=True,
            ),
            dbc.CardBody(
                [
                    html.H4(f"Ape {ape.asset_id.item()}"),
                    html.P(f"Listing Price {listing_eth} ETH"),
                    html.P(f"Predicted Price: {pred_eth} ETH"),
                    html.P(f"Rarity: {ape.rarity_rank.item()}"),
                    link,
                ]
            ),
        ],
        style={"width": "18rem"},
    )
