from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder

import opensea.database as db

router = APIRouter()


# create an endpoint to get sales for a given collection
@router.get("/sales/{collection}")
async def sales(collection: str, sale_min: float, n_top_results: int):
    query = {
        "sale_price": {"$gte": sale_min},
        "sale_currency": {"$in": ["ETH", "WETH"]},
    }

    sales = db.read_mongo(
        f"{collection}_sales",
        query_filter=query,
        return_df=True,
        query_limit=n_top_results,
        query_sort=[("time", -1)],
    )
    x = sales.sort_values("time", ascending=False).fillna("").to_dict(orient="records")

    return jsonable_encoder(x)
