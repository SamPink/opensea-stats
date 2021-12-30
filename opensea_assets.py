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


toucans = pd.DataFrame()
toucans_traits = pd.DataFrame()
for i in range(0, 2):
    response = get_opensea_asset(i)
    for toucan in response["assets"]:
        df = pd.json_normalize(toucan)
        traits = df.traits.item()
        tr = {}
        tr["name"] = df.name.item()
        for trait in traits:
            tr[trait["trait_type"]] = trait["value"]
        toucans_traits = toucans_traits.append(pd.DataFrame(tr, index=[0]))
        toucans = toucans.append(df)

# count number of traits of each apr
trait_list = [
    "Headwear",
    "Body",
    "Background",
    "Emotion",
    "Smoke",
    "Eyewear",
    "Neckwear",
    "Legendary Doge",
]
toucans_traits["trait_n"] = toucans_traits[trait_list].count(axis=1)

# calculate rarity (proportion of apes with each single trait)
apes = toucans_traits
apes_with_rarity = apes
for i in trait_list:
    apes_with_trait_i = apes[apes[i].notna()].shape[0]
    i_counts = apes[i].value_counts()
    i_proportion = i_counts / apes_with_trait_i
    apes_with_rarity = apes_with_rarity.merge(
        i_proportion, left_on=i, right_index=True, suffixes=("", "_rarity"), how="left"
    )

# calculate mean of all singe trait rarity
apes_with_rarity["mean_trait_rarity"] = apes_with_rarity[
    [
        "Headwear_rarity",
        "Body_rarity",
        "Background_rarity",
        "Emotion_rarity",
        "Smoke_rarity",
        "Eyewear_rarity",
        "Neckwear_rarity",
        "Legendary Doge_rarity",
    ]
].mean(axis=1)

# calculate rarity of most rare trait
apes_with_rarity["min_trait_rarity"] = apes_with_rarity[
    [
        "Headwear_rarity",
        "Body_rarity",
        "Background_rarity",
        "Emotion_rarity",
        "Smoke_rarity",
        "Eyewear_rarity",
        "Neckwear_rarity",
        "Legendary Doge_rarity",
    ]
].min(axis=1)

# calculate rarity of least rare trait
apes_with_rarity["max_trait_rarity"] = apes_with_rarity[
    [
        "Headwear_rarity",
        "Body_rarity",
        "Background_rarity",
        "Emotion_rarity",
        "Smoke_rarity",
        "Eyewear_rarity",
        "Neckwear_rarity",
        "Legendary Doge_rarity",
    ]
].max(axis=1)
