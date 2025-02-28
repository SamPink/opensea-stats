import dash_bootstrap_components as dbc
import pandas as pd
from dash import html, Input, Output, callback
from .assets.styles import Styles


layout = html.Div([
            html.Div(
                children=[
                    html.H1("Predicted Prices",
                        style=Styles.TITLE_STYLE_CENTER
                    )
                ],
                style=Styles.DIV_CENTERED_HOLDER
            ),
        html.Div(id="ape-stats-container"),
    ],
)


@callback(
    Output("ape-stats-container", "children"), [Input("store-best-listings", "data")]
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

    # round pred_eth up to nearest 0.01
    pred = round(ape.predicted_ETH.item(), 2)

    # round listing_eth up to nearest 0.01
    listing = round(ape.listing_price.item(), 2)

    return dbc.Card(
        [
            dbc.CardImg(
                src=ape.image_url.item(),
                top=True,
            ),
            dbc.CardBody(
                [
                    html.H4(f"Ape {ape.asset_id.item()}"),
                    html.P(f"Listing Price {listing} ETH"),
                    html.P(f"Predicted Price: {pred} ETH"),
                    html.P(f"Rarity: {ape.rarity_rank.item()}"),
                    dbc.CardLink("Opensea listing", href=ape.permalink.item()),
                ]
            ),
        ],
        style={"width": "18rem"},
    )
