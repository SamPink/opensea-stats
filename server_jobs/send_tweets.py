from twitter.sent_tweet import send_tweet_with_media

tweet = {
    "alienfrensnft": {
        "tweet": "hey frens, ive made a list of what I think are the best alien frens listed right now, do you agree with my findings?",
        "image": "sc_for_twitter/screenshot_alienfrensnft.png",
        "hashtag": "#alienfrens #Frens",
        "twitter_handle": "@alienfrens",
    },
    "world-of-women": {
        "tweet": "hey, ive made a list of what I think are the best World of Women listed right now, do you agree with my findings?",
        "image": "sc_for_twitter/screenshot_world-of-women-nft.png",
        "hashtag": "#WOWNFT #WOWNFT #worldofwomen #WomensArt",
        "twitter_handle": "@worldofwomennft",
    },
    "cryptomories": {
        "tweet": "hey mories, ive made a list of what I think are the best mories listed right now, do you agree with my findings?",
        "image": "sc_for_twitter/screenshot_cryptomories.png",
        "hashtag": "#FaMorie  #CryptoMories",
        "twitter_handle": "@CryptoMories",
    },
}


def send_tweet():

    col_to_tweet = "cryptomories"

    message = (
        tweet[col_to_tweet]["twitter_handle"]
        + "\n"
        + tweet[col_to_tweet]["tweet"]
        + "\n"
        + tweet[col_to_tweet]["hashtag"]
    )

    send_tweet_with_media(message, tweet[col_to_tweet]["image"])
