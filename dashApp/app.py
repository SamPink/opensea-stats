import datetime as dt

# importing sys
import sys

import dash
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

from pages import ape_sales

# adding Folder_2 to the system path
sys.path.insert(0, "./opensea")

from database import read_mongo

app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

# the style arguments for the sidebar. We use position:fixed and a fixed width
SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "16rem",
    "padding": "2rem 1rem",
    "background-color": "#f8f9fa",
}

# the styles for the main content position it to the right of the sidebar and
# add some padding.
CONTENT_STYLE = {
    "margin-left": "18rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
}

sidebar = html.Div(
    [
        html.H2("$GANG", className="display-4"),
        html.Hr(),
        html.P("Ape Gang Info", className="lead"),
        dbc.Nav(
            [
                dbc.NavLink("sales", href="/page-1", active="exact"),
                dbc.NavLink("stats", href="/page-2", active="exact"),
            ],
            vertical=True,
            pills=True,
        ),
    ],
    style=SIDEBAR_STYLE,
)

content = html.Div(id="page-content", style=CONTENT_STYLE)

app.layout = html.Div([dcc.Location(id="url"), sidebar, content])


@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def render_page_content(pathname):
    if pathname == "/":
        return html.P("This is the content of the home page!")
    elif pathname == "/page-1":
        return html.H1('d')
    elif pathname == "/page-2":
        return ape_sales.layout
    # If the user tries to reach a different page, return a 404 message
    return html.H1("FUCK")


def page_stats():
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
        query_limit=100,
        query_sort=[("time", -1)],
    )
    apes_old = read_mongo(
        "ape-gang-old_sales",
        return_df=True,
        query_projection=projection,
        query_limit=100,
        query_sort=[("time", -1)],
    )
    apes = apes.append(apes_old)
    apes = read_mongo("ape-gang-old_traits", return_df=True)

    sales = apes.append(apes_old)

    day_n = 30
    recent_sales = sales[sales.time > dt.datetime.now() - dt.timedelta(days=day_n)]
    recent_sales = (
        recent_sales[["asset_id", "sale_price", "time"]]
        .merge(apes, on="asset_id", how="left")
        .sort_values("sale_price", ascending=False)
    )

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

if __name__ == "__main__":
    app.run_server(port=1234)
