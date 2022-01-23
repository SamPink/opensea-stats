import io
from pandas import json_normalize
import time
import requests
import json
import pandas as pd
from math import ceil
import numpy as np
import re


from database import *


def get_opensea_asset(
    offset, collection, limit=50, api_key="3eb775e344f14798b49718e86f55608c"
):

    url = "https://api.opensea.io/api/v1/assets"

    params = {
        "collection_slug": collection,
        "offset": offset * 50,
        "limit": limit,
    }

    headers = {"Accept": "application/json", "X-API-KEY": api_key}

    response = requests.request("GET", url, params=params, headers=headers).json()

    return response


def get_opensea_metadata(collection, api_key="3eb775e344f14798b49718e86f55608c"):

    url = f"https://api.opensea.io/api/v1/collection/{collection}"

    headers = {"Accept": "application/json", "X-API-KEY": api_key}

    response = requests.request("GET", url, headers=headers).json()

    return response





def get_collection_assets(collection, id_col="token_id"):

    # work out how many loops to perform
    metadata = get_opensea_metadata(collection=collection)
    n_items = int(metadata["collection"]["stats"]["count"])
    n_api_calls = ceil(n_items / 50)  # calculate number of api calls we'll need to make
    print(
        f"{collection} has {n_items} NFTs, {n_api_calls} api calls will be made to retrieve the asset data."
    )

    # work out which traits the collection has
    traits = list(metadata["collection"]["traits"].keys())

    assets = pd.DataFrame()
    for i in range(0, n_api_calls):  # change this to get more assets
        response = get_opensea_asset(offset=i, collection=collection)
        if 'detail' in response.keys():
            time.sleep(5)
            print(response)
            response = get_opensea_asset(offset=i, collection=collection)
        for asset in response["assets"]:
            df = pd.json_normalize(asset)
            for t in asset["traits"]:
                df[t["trait_type"]] = t["value"]
            assets = assets.append(df)
        print(
            f"{i} of {n_api_calls} API calls have been made, {assets.shape[0]} {collection}'s retrieved!"
        )

    assets = assets.reset_index()

    # count number of traits of each apr
    assets_traits = assets[[id_col] + traits]

    # is id contained in string with # followed by digits
    first_id = assets_traits[id_col][0]
    if re.search("#\d+", first_id) is not None and isinstance(first_id, str):
        assets_traits = assets_traits.assign(
            asset_id=lambda x: x[id_col].str.extract("(\d+)")
        )
        assets_traits["asset_id"] = pd.to_numeric(assets_traits["asset_id"])

    assets_traits["trait_n"] = assets_traits[traits].count(axis=1)

    traits.append("trait_n")

    # calculate rarity (proportion of apes with each single trait)
    rarity = assets_traits.copy()

    for i in traits:
        i_proportion = assets_traits[i].value_counts(dropna=False, normalize=True)
        rarity = rarity.merge(
            i_proportion,
            left_on=i,
            right_index=True,
            suffixes=("", "_rarity"),
            how="left",
        )

    # create an array of the columns with the rarity
    rarity_list = [t + "_rarity" for t in traits]

    factorial_rarity = 1 / rarity[rarity_list]
    rarity["factoral_rarity"] = factorial_rarity.sum(axis=1)
    rarity = rarity.sort_values("factoral_rarity", ascending=False)
    rarity["rarity_rank"] = np.arange(1, rarity.shape[0] + 1, 1)

    write_mongo(
        collection=f"{collection}_traits",
        data=rarity,
        overwrite=True,
        database_name="mvh",
    )

    write_mongo(
        collection=f"{collection}_asset-all-info",
        data=assets,
        overwrite=True,
        database_name="mvh",
    )

