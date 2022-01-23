import dash
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime as dt

from dash import Dash, dcc, html, Input, Output, callback

import sys

sys.path.insert(0, "./opensea")

from database import read_mongo


def page_stats(opensea_data):
    recent_sales = pd.DataFrame(opensea_data)

    # create a plot of rank vs price
    fig = px.scatter(
        recent_sales,
        x="sale_price",
        y="rarity_rank",
        color="rarity_rank",
        hover_data=["asset_id", "sale_price", "time"],
        title="Rarity vs Price",
    )

    # plot mean price over time
    fig2 = px.line(recent_sales, x="time", y="sale_price")

    return html.Div(
        [
            html.H2("Ape Sales"),
            dcc.Graph(figure=fig),
            dcc.Graph(figure=fig2),
        ]
    )


layout = html.Div(
    [
        html.Div(id="ape-stats-container"),
    ]
)


@callback(Output("ape-stats-container", "children"), [Input("store-opensea", "data")])
def create_stats_page(opensea_data):
    if opensea_data is None:
        return None
    else:
        return page_stats(opensea_data)
