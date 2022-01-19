import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, dcc, html

# importing sys
import sys

import pandas as pd
import datetime as dt
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

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
        return page_apes(1)
    elif pathname == "/page-2":
        return page_stats()
    # If the user tries to reach a different page, return a 404 message
    return html.H1("FUCK")


# make a callback for dropdown
@app.callback(
    Output("ape-grid", "children"),
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


def page_apes(thing):

    dropdown_options = ["time", "price", "rarity"]

    # make a dropdown with the options
    dropdown = dcc.Dropdown(
        id="dropdown",
        options=[{"label": i, "value": i} for i in dropdown_options],
        value="time",
        style={"width": "50%"},
    )

    return html.Div(
        children=[
            html.H2(thing, id="title"),
            dropdown,
            dbc.Row(id="ape-grid"),
        ]
    )


def ape_grid(apes):
    return dbc.Row(
        [ape_card(apes.iloc[[i]]) for i in range(apes.shape[0])],
        id="ape-grid",
    )


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


if __name__ == "__main__":
    app.run_server(port=1234)
