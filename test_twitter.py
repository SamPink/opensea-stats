from twitter.gtp3 import request_davinci
from twitter.sent_tweet import send_tweet


tweet = request_davinci("What is the meaning of life?", 140)

send_tweet(tweet)
