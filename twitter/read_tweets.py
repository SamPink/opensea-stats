import os
from twython import Twython
from twython import TwythonStreamer
import csv
import pandas as pd
import json

# these are carves twitter credentials as i was trying to use the engagement api
# but idk how to do that yet so im using Twython
creds = {}
creds["CONSUMER_KEY"] = "vtTkftII8FhEW1vhKPfQ7gHtP"
creds["CONSUMER_SECRET"] = "LhHYaIx9WFMORFSOLmGGcJPYVHsLPEUTv0LITe46GsBwTaRElG"
creds["ACCESS_TOKEN"] = "1448093794541449218-aRO481gs2DvYNscc2iTUrfiVmsXHxe"
creds["ACCESS_SECRET"] = "IqiNyvyN57HFZx6hHzATXHbk2oZTRaT6Gsr4c9QaLVRvr"


def twitter_search(query):
    python_tweets = Twython(creds["CONSUMER_KEY"], creds["CONSUMER_SECRET"])
    # Search tweets
    dict_ = {"user": [], "date": [], "text": [], "favorite_count": []}
    for status in python_tweets.search(**query)["statuses"]:
        dict_["user"].append(status["user"]["screen_name"])
        dict_["date"].append(status["created_at"])
        dict_["text"].append(status["text"])
        dict_["favorite_count"].append(status["favorite_count"])

    # Structure data in a pandas DataFrame for easier manipulation
    df = pd.DataFrame(dict_)
    df.sort_values(by="favorite_count", inplace=True, ascending=False)
    return df


""" nft_tweets = twitter_search(
    {
        "q": "nft",
        "result_type": "popular",
        "count": 10,
        "lang": "en",
    }
)
 """

# Filter out unwanted data
def process_tweet(tweet):
    d = {}
    d["hashtags"] = [hashtag["text"] for hashtag in tweet["entities"]["hashtags"]]
    d["text"] = tweet["text"]
    d["user"] = tweet["user"]["screen_name"]
    d["user_loc"] = tweet["user"]["location"]
    d["user_followers"] = tweet["user"]["followers_count"]
    d["user_name"] = tweet["user"]["name"]
    d["user_screen_name"] = tweet["user"]["screen_name"]
    d["is_verified"] = tweet["user"]["verified"]
    d["profile_image_url"] = tweet["user"]["profile_image_url"]
    d["tweet_created_at"] = tweet["created_at"]
    d["tweet_quote_count"] = tweet["quote_count"]
    d["tweet_reply_count"] = tweet["reply_count"]
    d["tweet_retweet_count"] = tweet["retweet_count"]
    d["tweet_favorite_count"] = tweet["favorite_count"]

    return d


class MyStreamer(TwythonStreamer):

    # Received data
    def on_success(self, data):
        try:
            # Only collect tweets in English
            if data["lang"] == "en":
                tweet_data = process_tweet(data)
                self.save_to_csv(tweet_data)
        except Exception as e:
            print(e)
            print(data)

    # Problem with the API
    def on_error(self, status_code, data):
        print(status_code, data)
        self.disconnect()

    # Disconnect from Twitter API

    # Save each tweet to csv file
    def save_to_csv(self, tweet):
        with open(r"nfts_new.csv", "a") as file:
            # if first tweet, write header
            if os.stat(r"nfts_new.csv").st_size == 0:
                writer = csv.DictWriter(file, fieldnames=tweet.keys())
                writer.writeheader()
            writer = csv.writer(file)
            writer.writerow(list(tweet.values()))


def twitter_stream():
    stream = MyStreamer(
        creds["CONSUMER_KEY"],
        creds["CONSUMER_SECRET"],
        creds["ACCESS_TOKEN"],
        creds["ACCESS_SECRET"],
    )
    # TODO would make more sense if streamer returned a dataframe
    stream.statuses.filter(track="nft")
