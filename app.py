import uvicorn
from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi_utils.tasks import repeat_every
from ML.AgeGang_ML import update_ApeGang_pred_price
from ML.ApeGang_best_value import calc_best_apegang_listing
from ML.all_collection_best_value import calc_best_listing

from createdash import create_app

from api import endpoints, sales
from opensea.opensea_collections import (
    all_collection_names,
    all_collections_with_pred_price,
)
from opensea.opensea_events import update_opensea_events

app = FastAPI()
dash_app = create_app()

app.mount("/dash", WSGIMiddleware(dash_app.server))
""" import sys

# adding Folder_2 to the system path
sys.path.insert(0, "./opensea")


from opensea.database import read_mongo """

# set app title
app.title = "mvh.eth"

app.include_router(sales.router, prefix="/api/sales")
app.include_router(endpoints.router, prefix="/api")

# server.config.from_object(cfg)

DEBUG = True


@app.on_event("startup")
@repeat_every(seconds=60 * 60 * 6)  # repeat every 6 hours
def update_price_pred():
    # if app debug mode is off
    if not DEBUG:
        print("updating ApeGang Predicted price")
        update_ApeGang_pred_price()


@app.on_event("startup")
@repeat_every(seconds=60 * 10)  # repeat 10 mins
def update_events():
    # if not DEBUG:
    all_collections = all_collections_with_pred_price()
    # drop cryptopunks
    all_collections.remove("cryptopunks")
    for collection in all_collections:
        calc_best_listing(collection=collection, update_listings=True)

    nfts = all_collection_names()
    # nfts = ["ape-gang", "ape-gang-old", "boredapeyachtclub", "toucan-gang"]
    for x in nfts:
        print(f"updating {x} events")
        update_opensea_events(collection=x)

    # calc_best_apegang_listing(update_listings=True)
    # print("update apegang best listings")


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        debug=True,
        log_level="info",
        reload=True,
    )
