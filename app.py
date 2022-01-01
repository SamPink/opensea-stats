from fastapi import FastAPI
from database import read_mongo

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "#HODL #WAGMI"}


@app.get("/Welcome/")
def welcome_message(name: str):
    return {"message": f"Welcome {name}, #WAGMI"}


@app.get("/ApeGang USD price pred/")
def ape_id_query(ape_id: int):
    ApeGang_USD = read_mongo(
        "ape-gang-USD-value",
        query_filter={"asset_id": ape_id},
        query_projection={"_id": 0, "pred_USD": 1, "pred_USD_price_diff": 1},
    )
    return ApeGang_USD[0]
