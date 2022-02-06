import dash
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime as dt

from dash import Dash, dcc, html, Input, Output, callback


layout = html.Div(
    [
        html.Div(id="ape-stats-container"),
    ]
)


@callback(
    Output("ape-stats-container", "children"), [Input("store-predicted-value", "data")]
)
def create_stats_page(opensea_data):
    if opensea_data is None:
        return None
    else:
        # make a dataframe
        df = pd.DataFrame(opensea_data)
        df = df.head(100)
        # return html.Div([ape_card(df.iloc[[0]])])
        return html.Div(dbc.Row([ape_card(df.iloc[[i]]) for i in range(df.shape[0])]))


def ape_card(ape):
    print(ape.info())
    return dbc.Card(
        [
            dbc.CardImg(
                # src=ape.image_url.item(),
                top=True,
            ),
            dbc.CardBody(
                [
                    html.H4(f"Asset id {ape.asset_id.item()}"),
                    html.H4(f"Rarity rank {ape.rarity_rank.item()}"),
                    html.H4(f"Predictred USD {ape.predicted_USD.item()}"),
                    html.H4(f"Number of traits {ape.trait_n.item()}"),
                ]
            ),
        ],
        style={"width": "18rem"},
    )
