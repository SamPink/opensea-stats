# importing sys
import sys
import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, dcc, html

from pages import ape_sales, ape_stats

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
                dbc.NavLink("home", href="/"),
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

app.layout = html.Div(
    [
        dcc.Location(id="url"),
        sidebar,
        content,
        dcc.Store(id="store-opensea"),
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
    # If the user tries to reach a different page, return a 404 message
    return html.H1("FUCK")


def page_home():
    return html.Div(
        [
            html.H1("Hello World"),
            dcc.Dropdown(
                id="dropdown-collection",
                options=[
                    {"label": "Ape Gang", "value": "ape-gang"},
                    {"label": "BAYC", "value": "boredapeyachtclub"},
                ],
                style={"width": "50%"},
            ),
        ]
    )


# create a callback for the dropdown
@app.callback(
    Output("store-opensea", "data"),
    [Input("dropdown-collection", "value")],
)
def get_opensea(collection):
    if collection is None:
        return None
    print(collection)
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
        f"{collection}_sales",
        return_df=True,
        query_projection=projection,
        query_limit=1000,
        query_sort=query_sort,
    )
    print(apes.head())
    """ apes_old = read_mongo(
        "ape-gang-old_sales",
        return_df=True,
        query_projection=projection,
        query_limit=1000,
        query_sort=query_sort,
    ) """
    # apes = apes.append(apes_old)

    # it seems read mongo cant filter on a list, why it do dis?
    # ape_ids = apes.asset_id.unique().tolist()

    apes_rarity = read_mongo(
        f"{collection}_traits",
        return_df=True,
        # query_filter={"asset_id": {"$in": ape_ids}},
    )
    print(apes_rarity.head())

    """ ApeGang_USD = read_mongo(
        "ape-gang-USD-value",
        query_projection=["asset_id", "pred_USD", "pred_USD_price_diff"],
        return_df=True,
    ) """

    # join Apes and ApeGang_USD
    # apes = apes.merge(ApeGang_USD, on="asset_id")

    # join apes_rarity to apes
    apes = apes.merge(apes_rarity, on="asset_id")

    # drop duplicates
    apes = apes.drop_duplicates()

    print(apes.head())

    return apes.to_dict("records")


if __name__ == "__main__":
    app.run_server(port=1235, debug=True)
