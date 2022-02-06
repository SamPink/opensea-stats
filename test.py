# importing sys
import sys

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, dcc, html

from pages import ape_sales, ape_stats, best_apes_listed, predicted_value

# adding Folder_2 to the system path
sys.path.insert(0, "./opensea")

from opensea.database import read_mongo
from opensea.opensea_collections import all_collection_names


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
                    dbc.NavLink("home", href="/"),
                    dbc.NavLink("sales", href="/page-1", active="exact"),
                    dbc.NavLink("stats", href="/page-2", active="exact"),
                    dbc.NavLink(
                        "best Ape Gang listings",
                        href="/apes-best-listings",
                        active="exact",
                    ),
                    dbc.NavLink(
                        "predicted price",
                        href="/predicted-price",
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
            dcc.Store(id="store-predicted-value"),
        ]
    )

    @app.callback(Output("page-content", "children"), [Input("url", "pathname")])
    def render_page_content(pathname):
        if pathname == "/":
            return page_home()
        elif pathname == "/page-1":
            return ape_stats.layout
        elif pathname == "/page-2":
            return ape_sales.layout
        elif pathname == "/apes-best-listings":
            return best_apes_listed.page_best_listings()
        elif pathname == "/predicted-price":
            return predicted_value.layout
        # If the user tries to reach a different page, return a 404 message
        return html.H1("FUCK")

    def page_home():
        all_collections = all_collection_names()

        # create a options list for the dropdown
        options = [
            {"label": collection, "value": collection} for collection in all_collections
        ]
        return html.Div(
            [
                html.H1("Hello World"),
                dcc.Dropdown(
                    id="dropdown-collection",
                    options=options,
                    style={"width": "50%"},
                ),
            ]
        )

    # create a callback for the dropdown
    @app.callback(
        [
            Output("store-opensea-sales", "data"),
            Output("store-predicted-value", "data"),
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

        value = read_mongo(
            f"{collection}_predicted_USD",
            return_df=True,
        )

        if value is None or value.empty:
            # no predicted value
            value = None

        return sales.to_dict("records"), value.to_dict("records")

    return app
