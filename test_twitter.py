from twitter.gtp3 import request_davinci
from twitter.sent_tweet import send_tweet

from opensea.database import read_mongo

import pandas as pd


tweet = request_davinci(
    "write a tweet about #ETH",
    140,
)

all_collections = [
    "cool-cats-nft",
    "the-doge-pound",
    "world-of-women-nft",
    "supducks",
    "cryptoadz-by-gremplin",
    "rumble-kong-league",
    "ape-gang-old",
]

# read mongo for each of the collections in this array
best_listings = pd.DataFrame()
for col in all_collections:
    df = read_mongo(col, return_id=False, return_df=True)

    best_listings = best_listings.append(df)


# send_tweet(tweet)
