# importing sys
import sys

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, dcc, html

import pandas as pd

from pages import (
    best_apes_listed,
    predicted_value,
    sales_history_graph,
    sales_history_grid,
)

from pages.assets.styles import Styles

# adding Folder_2 to the system path
sys.path.insert(0, "./opensea")

from opensea.database import read_mongo
from opensea.opensea_collections import all_collections_with_pred_price
from opensea.opensea_assets import get_from_collection


def page_home():
    # all_collections = all_collections_with_pred_price()

    all_collections = [
        "cool-cats-nft",
        "the-doge-pound",
        "world-of-women-nft",
        "supducks",
        "cryptoadz-by-gremplin",
        "rumble-kong-league",
        "pepsi-mic-drop",
        "deadfellaz",
        "doodledogsofficial",
        "robotos-official",
        "azuki",
        "alpacadabraz",
    ]

    # create a options list for the dropdown
    options = [
        {"label": collection, "value": collection} for collection in all_collections
    ]
    return html.Div(
        [
            html.Div(
                children=[
                    html.H1(
                        "Choose your collection:",
                        style=Styles.SUB_TITLE_STYLE,
                    ),
                    dcc.Dropdown(
                        id="dropdown-collection",
                        options=options,
                        # style=Styles.DROPDOWN_BOX_STYLE,
                    ),
                ],
                style=Styles.DIV_CENTERED_HOLDER,
            ),
        ],
    )


def create_app():
    app = dash.Dash(
        external_stylesheets=[dbc.themes.BOOTSTRAP], requests_pathname_prefix="/dash/"
    )

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
                    dbc.NavLink("Home", href="/dash"),
                    dbc.NavLink("Sales history", href="/sales-history", active="exact"),
                    dbc.NavLink("Sales graph", href="/sales-graph", active="exact"),
                    dbc.NavLink("Predicted", href="/predicted-value", active="exact"),
                    dbc.NavLink(
                        "Best Listings",
                        href="/apes-best-listings",
                        active="exact",
                    ),
                ],
                vertical=True,
                pills=True,
            ),
        ],
        style=SIDEBAR_STYLE,
    )

    content = html.Div(id="page-content", style=CONTENT_STYLE)

    app.layout = html.Div(
        [
            dcc.Location(id="url"),
            sidebar,
            content,
            dcc.Store(id="store-opensea-sales"),
            dcc.Store(id="store-best-listings"),
        ]
    )

    @app.callback(Output("page-content", "children"), [Input("url", "pathname")])
    def render_page_content(pathname):
        if pathname == "/" or pathname == "/dash/":
            return page_home()
        elif pathname == "/predicted-value":
            return predicted_value.layout
        elif pathname == "/sales-history":
            return sales_history_grid.layout
        elif pathname == "/apes-best-listings":
            return best_apes_listed.page_best_listings()
        elif pathname == "/sales-graph":
            return sales_history_graph.layout

        # If the user tries to reach a different page, return a 404 message
        return html.H1("FUCK")

    # create a callback for the dropdown
    @app.callback(
        [
            Output("store-opensea-sales", "data"),
            Output("store-best-listings", "data"),
        ],
        [Input("dropdown-collection", "value")],
    )
    def get_opensea(collection):
        if collection is None:
            return None

        sales = read_mongo(
            f"{collection}_sales",
            return_df=True,
            query_projection={
                "_id": 0,
                "asset_id": 1,
                "image_url": 1,
                "sale_price": 1,
                "buyer_wallet": 1,
                "time": 1,
            },
            query_limit=10000,
            query_sort=[("time", -1)],
        ).drop_duplicates(subset=["asset_id"])

        if sales is None or sales.empty:
            print(f"No sales data for {collection}")
            return None

        asset_cols = get_from_collection(
            collection=collection,
            col_to_return=["image_url", "permalink"],
            id_col="asset_id",
        )
        if asset_cols is None or asset_cols.empty:
            asset_cols = get_from_collection(
                collection=collection,
                col_to_return=["image_url", "permalink"],
            )

        best_listed = read_mongo(
            f"{collection}_bestvalue_opensea_listings",
            return_df=True,
            query_projection={
                "_id": 0,
            },
            query_sort=[("listing_value", -1)],
        )

        if best_listed is None or best_listed.empty:
            print(f"No best listed data for {collection}")
            best_listed = pd.DataFrame()

        # join asset_cols on asset_id to best_listed
        best_listed = best_listed.merge(asset_cols, on="asset_id")

        return (
            sales.to_dict("records"),
            best_listed.to_dict("records"),
        )

    return app
