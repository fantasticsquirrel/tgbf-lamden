import logging
import tweepy
import time
import json


class TwitterBot:
    api = None

    def __init__(self, consumer_key: str, consumer_sec: str, access_token_key: str, access_token_sec: str):
        # Set credentials for Twitter access
        auth = tweepy.OAuth1UserHandler(consumer_key, consumer_sec)
        auth.set_access_token(access_token_key, access_token_sec)

        # Authenticate
        self.api = tweepy.API(auth)
        print(self.api.verify_credentials().screen_name)

        # Create stream
        stream = ReplyStream(consumer_key, consumer_sec, access_token_key, access_token_sec, self.api)

        # Filter on bot username
        stream.filter(track=[f"@{self.api.verify_credentials().screen_name}"], threaded=True)

        while True:
            time.sleep(0.01)

    def update_status(self, message: str):
        self.api.update_status(message)


class ReplyStream(tweepy.Stream):
    api = None

    def __init__(self, consumer_key, consumer_sec, access_token_key, access_token_sec, api):
        super().__init__(consumer_key, consumer_sec, access_token_key, access_token_sec)
        self.api = api

    def on_data(self, raw_data):
        print("raw_data", raw_data)

        data = json.loads(raw_data)
        user = data["user"]["id"]

    def on_exception(self, exception):
        logging.error(f'Error in Twitter Bot: {exception}')
