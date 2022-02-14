import time
import requests
import pandas as pd
from math import ceil
import numpy as np
import re

import os, sys


currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)
from opensea.database import *
from opensea.opensea_collections import *


def check_response(url, headers, params=None, method="GET"):
    response = requests.request(method, url, params=params, headers=headers)
    if response.ok:
        return response.json()
    elif response.status_code == 429:
        for attempt_x in range(1, 50):
            print(f"being rated limited...attempt {attempt_x}")
            time.sleep(5 * attempt_x)  # wait 20 seconds * number of loops
            response = requests.request(method, url, params=params, headers=headers)
            if response.ok:
                return response.json()
    else:

        # wait 10 seconds and try again
        time.sleep(10)
        response = requests.request(method, url, params=params, headers=headers)
        if response.ok:
            return response.json()
        else:
            # if still nothing, return error
            print(
                f"Error in Opensea Events API call. Status code {response.status_code}."
            )
            print(response)
            return None


def get_opensea_asset(
    offset,
    collection,
    limit=50,
    api_key="3eb775e344f14798b49718e86f55608c",
    token_ids=None,
):

    url = "https://api.opensea.io/api/v1/assets"

    params = {
        "collection_slug": collection,
        "offset": offset * limit,
        "limit": limit,
    }
    if token_ids is not None:
        params["token_ids"] = [str(x) for x in token_ids]
        params["limit"] = 30

    headers = {"Accept": "application/json", "X-API-KEY": api_key}

    response = check_response(url=url, params=params, headers=headers)
    return response


def get_opensea_metadata(collection, api_key="3eb775e344f14798b49718e86f55608c"):

    url = f"https://api.opensea.io/api/v1/collection/{collection}"

    headers = {"Accept": "application/json", "X-API-KEY": api_key}

    response = check_response(url=url, headers=headers)
    return response


def get_collection_assets(collection, offset=0):
    opensea_call_limit = 201
    # work out how many loops to perform
    metadata = get_opensea_metadata(collection=collection)
    n_items = int(metadata["collection"]["stats"]["count"])
    n_api_calls = ceil(n_items / 50)  # calculate number of api calls we'll need to make

    # work out which traits the collection has
    traits = list(metadata["collection"]["traits"].keys())
    if n_api_calls <= opensea_call_limit:
        print(
            f"{collection} has {n_items} NFTs, {n_api_calls} api calls will be made to retrieve the asset data."
        )
        assets = pd.DataFrame()
        for i in range(offset, n_api_calls):  # change this to get more assets
            response = get_opensea_asset(offset=i, collection=collection)
            # check that response is all good
            if "assets" not in response.keys():
                time.sleep(3)
                print(response)
                response = get_opensea_asset(offset=i, collection=collection)
            for asset in response["assets"]:
                df = pd.json_normalize(asset)
                for t in asset["traits"]:
                    df[t["trait_type"]] = t["value"]
                assets = assets.append(df)
            print(
                f"{i} of {n_api_calls+1} API calls have been made, {assets.shape[0]} {collection}'s retrieved!"
            )
    else:
        assets = pd.DataFrame()
        n_api_calls = ceil(n_items / 30)  # 30 limit when specifying token IDs
        print(
            f"{collection} has {n_items} NFTs, {n_api_calls} api calls will be made to retrieve the asset data."
        )
        for i in range(offset, n_api_calls):
            TokenIds2get = list(range((i * 30) + 1, (i * 30) + 31))
            response = get_opensea_asset(
                offset=0, collection=collection, token_ids=TokenIds2get
            )
            # check that response is all good
            if "assets" not in response.keys():
                time.sleep(3)
                print(response)
                response = get_opensea_asset(offset=i, collection=collection)
            for asset in response["assets"]:
                df = pd.json_normalize(asset)
                for t in asset["traits"]:
                    df[t["trait_type"]] = t["value"]
                assets = assets.append(df)
            print(
                f"{i+1} of {n_api_calls} API calls have been made, {assets.shape[0]} {collection}'s retrieved!"
            )

    # auto detect asset id
    name = assets.name.iloc[0]
    id = int(assets.token_id.iloc[0])

    if id < 1e6:
        assets["asset_id"] = assets["token_id"].astype(int)
    elif id > 1e6 and re.search("#\d+", name):
        assets["asset_id"] = (
            assets["name"].str.split("#", n=2, expand=True)[1].astype(int)
        )
    else:
        assets["asset_id"] = name

    assets = assets.reset_index()

    # count number of traits of each apr
    assets_traits = assets.copy()[
        ["asset_id", "name", "image_url", "permalink", "collection.name"] + traits
    ]

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


def get_from_collection(collection, id_col="token_id", col_to_return=["image_url"]):
    # if collection name contains ape-gang
    if re.search("ape-gang", collection):
        id_col = "name"

    query_projection = {
        "_id": 0,
        id_col: 1,
    }

    # add the columns to return
    for col in col_to_return:
        query_projection[col] = 1

    try:

        assets = read_mongo(
            collection=f"{collection}_asset-all-info",
            return_df=True,
            query_projection=query_projection,
        )

        assets = assets.reset_index()
        assets = assets.rename(columns={id_col: "asset_id"})

        # is id contained in string with # followed by digits
        first_id = assets["asset_id"][0]
        if re.search("#\d+", str(first_id)) is not None and isinstance(first_id, str):
            assets = assets.assign(
                asset_id=lambda x: x["asset_id"].str.extract("(\d+)")
            )
            assets["asset_id"] = pd.to_numeric(assets["asset_id"])
        else:

            assets["asset_id"] = assets["asset_id"].astype(int)

        return assets
    except Exception as e:
        print(e)
        return None
