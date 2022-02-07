import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, callback
import pandas as pd


layout = html.Div(
    [
        html.H1("Hello World"),
        html.Div(
            id="fig",
        ),
    ]
)


@callback(
    Output("fig", "children"),
    [Input("store-opensea-sales", "data")],
)
def update_output(opensea_data):
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

        return dcc.Graph(figure=fig)
