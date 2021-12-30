import io
from pandas import json_normalize
import requests
import json
import pandas as pd


def get_opensea_asset(
    offset=0, collection="boredapeyachtclub", api_key="3eb775e344f14798b49718e86f55608c"
):

    url = "https://api.opensea.io/api/v1/assets"

    params = {
        "collection_slug": collection,
        "offset": offset * 50,
        "limit": 50,
    }

    headers = {"Accept": "application/json", "X-API-KEY": api_key}

    response = requests.request("GET", url, params=params, headers=headers).json()

    return response


assets = pd.DataFrame()
assets_traits = pd.DataFrame()
for i in range(0, 2):  # change this to get more assets
    response = get_opensea_asset(i)
    for asset in response["assets"]:
        df = pd.json_normalize(asset)
        traits = df.traits.item()
        tr = {}
        tr["name"] = df.name.item()
        for trait in traits:
            tr[trait["trait_type"]] = trait["value"]
        assets_traits = assets_traits.append(pd.DataFrame(tr, index=[0]))
        assets = assets.append(df)

# count number of traits of each apr
trait_list = assets_traits.columns

assets_traits["trait_n"] = assets_traits[trait_list].count(axis=1)

# calculate rarity (proportion of apes with each single trait)
apes = assets_traits
apes_with_rarity = apes
for i in trait_list:
    apes_with_trait_i = apes[apes[i].notna()].shape[0]
    i_counts = apes[i].value_counts()
    i_proportion = i_counts / apes_with_trait_i
    apes_with_rarity = apes_with_rarity.merge(
        i_proportion, left_on=i, right_index=True, suffixes=("", "_rarity"), how="left"
    )

# create an array of the columns with the rarity
rarity_list = []
for i in trait_list:
    rarity_list.append(i + "_rarity")


# calculate mean of all singe trait rarity
apes_with_rarity["mean_trait_rarity"] = apes_with_rarity[rarity_list].mean(axis=1)

# calculate rarity of most rare trait
apes_with_rarity["min_trait_rarity"] = apes_with_rarity[rarity_list].min(axis=1)

# calculate rarity of least rare trait
apes_with_rarity["max_trait_rarity"] = apes_with_rarity[rarity_list].max(axis=1)

print(apes_with_rarity)
