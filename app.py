from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder

from database import read_mongo


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "#HODL #WAGMI"}


@app.get("/Welcome/")
def welcome_message(name: str):
    return {"message": f"Welcome {name}, #WAGMI"}


@app.get("/ApeGang USD price pred/")
async def ape_id_query(ape_id: int):
    ApeGang_USD = read_mongo(
        "ape-gang-USD-value",
        query_filter={"asset_id": ape_id},
        query_projection=["pred_USD", "pred_USD_price_diff"],
    )
    return ApeGang_USD[0]


@app.get("/ApeGang-best-value-listings/")
async def AG_best_listings(n_top_results: int):
    x = read_mongo(
        collection="ape-gang_bestvalue_opensea_listings",
        query_limit=n_top_results,
        return_df=True,
    )
    x = x.fillna("").to_dict(orient="records")

    return jsonable_encoder(x)
