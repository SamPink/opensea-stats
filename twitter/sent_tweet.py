import tweepy

consumer_key = "cD38eUo81kmPFGzof7xsqxybf"
consumer_secret = "NzSTcLfqv7kmDTYadmrUwBH1hG4F3dNueByxzSMdr9fxvh9jI0"
access_token = "3367576000-opWncXuBVZRWsvfVybmf2PK97cpM7wOQT9ht8F3"
access_token_secret = "ulVlHsXgEY2wzT2nroD87n2dSkmI2ZeGsLm5EBaOX7zha"


def connect_twitter():
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    return tweepy.API(auth)


def tweet_multi(tweet):
    twitter = connect_twitter()
    # split tweet into 140 characters
    tweet_list = [tweet[i : i + 140] for i in range(0, len(tweet), 140)]
    sent = twitter.update_status(tweet_list[0])
    # reply to tweet with each item in tweet_list
    for i in range(1, len(tweet_list)):
        twitter.update_status(tweet_list[i], in_reply_to_status_id=sent.id)


def send_tweet(tweet):
    twitter = connect_twitter()
    # send tweet
    return twitter.update_status(tweet)


def send_tweet_with_media(tweet, image_path):
    twitter = connect_twitter()
    # send tweet with media
    return twitter.update_status_with_media(tweet, image_path)
