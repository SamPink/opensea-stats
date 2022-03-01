from twitter.gtp3 import request_davinci
from twitter.sent_tweet import send_tweet

from opensea.database import read_mongo

import pandas as pd


tweet = request_davinci(
    "write a tweet about #ETH",
    140,
)



send_tweet(tweet)
