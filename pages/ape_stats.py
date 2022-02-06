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
    Output("ape-stats-container", "children"), [Input("store-opensea-sales", "data")]
)
def create_stats_page(opensea_data):
    if opensea_data is None:
        return None
    else:
        sales = pd.DataFrame(opensea_data)

        # convert to datetime
        sales["time"] = pd.to_datetime(sales["time"])

        # convert sale_time to date
        sales["sale_date"] = sales["time"].dt.date

        # get the min sale price for each day
        sales_min = sales.groupby(["sale_date"])["sale_price"].min()

        # plot the min sale price for each day excluding days with no sales
        fig = go.Figure(data=[go.Scatter(x=sales_min.index, y=sales_min.values)])
        # add 5 day moving average
        fig.add_trace(go.Scatter(x=sales_min.index, y=sales_min.rolling(5).mean()))
        # name figure floor by day
        fig.update_layout(title_text="Floor Price by Day")

        return html.Div(
            [
                html.H2("Ape Sales"),
                dcc.Graph(figure=fig),
            ]
        )
