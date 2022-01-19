import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, dcc, html

# importing sys
import sys

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
        html.H2("Sidebar", className="display-4"),
        html.Hr(),
        html.P("A simple sidebar layout with navigation links", className="lead"),
        dbc.Nav(
            [
                dbc.NavLink("Home", href="/", active="exact"),
                dbc.NavLink("Page 1", href="/page-1", active="exact"),
                dbc.NavLink("Page 2", href="/page-2", active="exact"),
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
        return html.P("Oh cool, this is page 2!")
    # If the user tries to reach a different page, return a 404 message
    return html.H1("FUCK")


# make a callback for dropdown
@app.callback(
    Output("title", "value"),
    [Input("dropdown", "value")],
)
def update_output(value):
    page_apes(1)


def page_apes(thing):
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
        query_limit=20,
        query_sort=[("time", -1)],
    )
    apes_old = read_mongo(
        "ape-gang-old_sales",
        return_df=True,
        query_projection=projection,
        query_limit=20,
        query_sort=[("time", -1)],
    )
    apes_rarity = read_mongo(
        "ape-gang-old_traits",
        return_df=True,
    )

    apes = apes.append(apes_old)

    # it seems read mongo cant filter on a list, why it do dis?
    ape_ids = apes.asset_id.unique()

    ApeGang_USD = read_mongo(
        "ape-gang-USD-value",
        query_projection=["asset_id", "pred_USD", "pred_USD_price_diff"],
        return_df=True,
    )

    # join Apes and ApeGang_USD
    apes = apes.merge(ApeGang_USD, on="asset_id")

    # join apes_rarity to apes
    apes = apes.merge(apes_rarity, on="asset_id")

    # sort by time
    apes = apes.sort_values(by=["time"], ascending=False)

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
            dbc.Row(
                [ape_card(apes.iloc[[i]]) for i in range(apes.shape[0])],
            ),
        ]
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
