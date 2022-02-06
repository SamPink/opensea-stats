from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder

import opensea.database as db

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "#HODL #WAGMI"}


@router.get("/Welcome/")
def welcome_message(name: str):
    return {"message": f"Welcome {name}, #WAGMI"}


@router.get("/ApeGang USD price pred/")
async def ape_id_query(ape_id: int):
    ApeGang_USD = db.read_mongo(
        "ape-gang-USD-value",
        query_filter={"asset_id": ape_id},
        query_projection=["pred_USD", "pred_USD_price_diff"],
    )
    return ApeGang_USD[0]


@router.get("/ApeGang-best-value-listings/")
async def AG_best_listings(n_top_results: int):
    x = db.read_mongo(
        collection="ape-gang_bestvalue_opensea_listings",
        query_limit=n_top_results,
        return_df=True,
    )
    x = x.fillna("").to_dict(orient="records")

    return jsonable_encoder(x)


def query_builder(query_filter, query_projection, query_sort, query_limit):
    return {
        "filter": query_filter,
        "projection": query_projection,
        "sort": query_sort,
        "limit": query_limit,
    }


@router.get("/ApeGang-Sales/")
async def AG_sales(sale_min: float, n_top_results: int):
    AG_query = {
        "sale_price": {"$gte": sale_min},
        "sale_currency": {"$in": ["ETH", "WETH"]},
    }

    AG_old = db.read_mongo(
        "ape-gang-old_sales",
        query_filter=AG_query,
        return_df=True,
        query_limit=n_top_results,
        query_sort=[("time", -1)],
    )
    AG_new = db.read_mongo(
        "ape-gang_sales",
        query_filter=AG_query,
        return_df=True,
        query_limit=n_top_results,
        query_sort=[("time", -1)],
    )
    AG_sales = (
        AG_old.append(AG_new)
        .sort_values("time", ascending=False)
        .fillna("")
        .head(n_top_results)
        .to_dict(orient="records")
    )

    return jsonable_encoder(AG_sales)


@router.get("/Toucan-Sales/")
async def Toucan_sales(sale_min: float, n_top_results: int):
    query = {
        "sale_price": {"$gte": sale_min},
        "sale_currency": {"$in": ["ETH", "WETH"]},
    }

    toucans = db.read_mongo(
        "toucan-gang_sales",
        query_filter=query,
        return_df=True,
        query_limit=n_top_results,
        query_sort=[("time", -1)],
    )
    x = (
        toucans.sort_values("time", ascending=False)
        .fillna("")
        .to_dict(orient="records")
    )

    return jsonable_encoder(x)


@router.get("/BAYC-Sales/")
async def BAYC_sales(sale_min: float, n_top_results: int):
    query = {
        "sale_price": {"$gte": sale_min},
        "sale_currency": {"$in": ["ETH", "WETH"]},
    }

    BAYC = db.read_mongo(
        "boredapeyachtclub_sales",
        query_filter=query,
        return_df=True,
        query_limit=n_top_results,
        query_sort=[("time", -1)],
    )
    x = BAYC.sort_values("time", ascending=False).fillna("").to_dict(orient="records")

    return jsonable_encoder(x)
