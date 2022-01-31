from database import read_mongo, write_mongo


ape_gang_all = read_mongo(
    "ape-gang-old_asset-all-info",
    return_df=True,
    query_projection=["name", "image_url"],
)

ape_gang_traits = read_mongo(
    "ape-gang-old_traits",
    return_df=True,
)

# use regex to get asset_id int from name
ape_gang_all["asset_id"] = ape_gang_all["name"].str.extract(r"(\d+)")

# convert asset_id to int
ape_gang_all["asset_id"] = ape_gang_all["asset_id"].astype(int)

# merge traits to all
ape_gang_all = ape_gang_all.merge(ape_gang_traits, on="asset_id", how="left")

print(ape_gang_all.head())

write_mongo("ape-gang-old_traits", ape_gang_all, overwrite=True)
