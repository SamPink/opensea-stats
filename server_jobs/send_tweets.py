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
    "doodles-official": {
        "tweet": "hey doodle fam, ive made a list of the best doodles listings right now. do you guys agree with the listings ive chosen?",
        "image": "sc_for_twitter/screenshot_doodles-official.png",
        "hashtag": "#Doodles #spacedoodle #doodlesfollowdoodles #gm ",
        "twitter_handle": "@doodles",
    },
    "rumble-kong-league": {
        "tweet": "hey kongs, ive made a list of what I think are the best value kong listings right now, do you agree with my findings?",
        "image": "sc_for_twitter/screenshot_rumble-kong-league.png",
        "hashtag": "#rumblekongs #iamkong",
        "twitter_handle": "@RumbleKongs",
    },
    "supducks": {
        "tweet": "hey supducks, ive made a list of what I think are the best supducks listings right now, do you agree with my findings?",
        "image": "sc_for_twitter/screenshot_supducks.png",
        "hashtag": "#Sup #SUPSUPSUP #SupDucks #supducks",
        "twitter_handle": "@RealSupDucks",
    },
    "mfers": {
        "tweet": "Hey mfers, ive made a quick analysis of the best value mfers listed. do mfers agree with my findings?",
        "image": "sc_for_twitter/screenshot_mfers.png",
        "hashtag": "#NFT #mfer #mfers",
        "twitter_handle": "@sartoshi_nft",
    },
}


def send_all_tweets():
    # loop through all keys in tweet dict
    for key in tweet:
        send_tweet(col_to_tweet=key)


def send_tweet(col_to_tweet="mfers"):
    message = (
        tweet[col_to_tweet]["tweet"]
        + "\n"
        + tweet[col_to_tweet]["twitter_handle"]
        + "\n"
        + tweet[col_to_tweet]["hashtag"]
    )

    send_tweet_with_media(message, tweet[col_to_tweet]["image"])
