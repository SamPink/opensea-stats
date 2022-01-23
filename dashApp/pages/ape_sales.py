import dash
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output, callback
import pandas as pd
import sys

sys.path.insert(0, "./opensea")

from database import read_mongo

dropdown_options = [
    {"label": "price", "value": "sale_price"},
    {"label": "time", "value": "time"},
    {"label": "rarity", "value": "rarity_rank"},
]

# make a dropdown with the options
dropdown = dcc.Dropdown(
    id="dropdown",
    options=dropdown_options,
    value="time",
    style={"width": "50%"},
)

layout = html.Div(
    [
        html.H1("Hello World"),
        html.H2(id="title"),
        dropdown,
        html.Div(
            id="card-container",
        ),
    ]
)

""" if value == "price":
        query_sort = [("sale_price", -1)]
    elif value == "time":
        query_sort = [("time", -1)]
    else:
        query_sort = [("time", -1)] """


@callback(
    Output("card-container", "children"),
    [Input("store-opensea", "data"), Input("dropdown", "value")],
)
def update_output(opensea_data, value):
    if opensea_data is None:
        return None
    else:
        # make a dataframe
        df = pd.DataFrame(opensea_data)
        # sort by the value of the dropdown
        df = df.sort_values(by=value, ascending=False)
        print(df)
        df = df.head(100)
        # return html.Div([ape_card(df.iloc[[0]])])
        return html.Div(dbc.Row([ape_card(df.iloc[[i]]) for i in range(df.shape[0])]))


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
