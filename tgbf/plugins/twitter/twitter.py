import logging
import tweepy
import json
import tgbf.emoji as emo

from tgbf.plugin import TGBFPlugin, WalletType
from tgbf.lamden.connect import Connect


class Twitter(TGBFPlugin):
    client = None

    def load(self):
        if not self.global_table_exists("tw_wallets", db_name="twitter"):
            sql = self.get_global_resource("create_tw_wallets.sql")
            self.execute_global_sql(sql, db_name="twitter")

        con_key = self.config.get("consumer_key")
        con_sec = self.config.get("consumer_sec")
        acc_tkn_key = self.config.get("access_token_key")
        acc_tkn_sec = self.config.get("access_token_sec")

        self.client = tweepy.Client(
            consumer_key=con_key,
            consumer_secret=con_sec,
            access_token=acc_tkn_key,
            access_token_secret=acc_tkn_sec
        )

        stream = ReplyStream(con_key, con_sec, acc_tkn_key, acc_tkn_sec, self.client, self)
        stream.filter(track=[f"@{self.client.get_me().data['username']}"], threaded=True)


class ReplyStream(tweepy.Stream):
    client = None
    plugin = None

    def __init__(self, con_key, con_sec, acc_tkn_key, acc_tkn_sec, client, plugin: Twitter):
        super().__init__(con_key, con_sec, acc_tkn_key, acc_tkn_sec)
        self.client = client
        self.plugin = plugin

    def on_data(self, raw_data):
        tweet = json.loads(raw_data)
        logging.debug(f'ReplyStream - on_data()', tweet)

        from_user = tweet["user"]["screen_name"].lower()

        wallet = self.plugin.get_wallet(from_user, WalletType.TWITTER)
        lamden = Connect(wallet)

        text = tweet["text"].lower()
        text_list = text.split()

        command = text_list[1]

        # TIP
        if command == "tip":
            amount = text_list[2]
            to = text_list[3]

            if to.startswith("@"):
                to_address = self.plugin.get_wallet(to[1:], WalletType.TWITTER).verifying_key
            else:
                self.client.create_tweet(
                    in_reply_to_tweet_id=tweet["id"],
                    text=self.plugin.get_usage())
                return

            res = lamden.send(amount, to_address)

            if "error" in res:
                msg = f"{emo.ERROR} Transaction error: {res['error']}"
                logging.error(msg)
                self.client.create_tweet(
                    in_reply_to_tweet_id=tweet["id"],
                    text=msg)
                return

            msg = f'{emo.MONEY} Tipped {amount} $TAU to {to}\n ' + \
                  f'{lamden.explorer_url}/transactions/{res["hash"]}'

            self.client.create_tweet(
                in_reply_to_tweet_id=tweet["id"],
                text=msg)

        # ADDRESS
        elif command == "address":
            address = self.plugin.get_wallet(from_user, WalletType.TWITTER).verifying_key

            self.client.create_tweet(
                in_reply_to_tweet_id=tweet["id"],
                text=f"Your #Lamden address: {address}")

        elif command == "send":
            amount = text_list[2]
            to = text_list[3]

            if not lamden.is_address_valid(to):
                self.client.create_tweet(
                    in_reply_to_tweet_id=tweet["id"],
                    text=f"{emo.ERROR} Not a valid #Lamden address")
                return

            res = lamden.send(amount, to)

            if "error" in res:
                msg = f"{emo.ERROR} Transaction error: {res['error']}"
                logging.error(msg)
                self.client.create_tweet(
                    in_reply_to_tweet_id=tweet["id"],
                    text=msg)
                return

            msg = f'{emo.MONEY} Sent {amount} $TAU to {to}\n ' + \
                  f'{lamden.explorer_url}/transactions/{res["hash"]}'

            self.client.create_tweet(
                in_reply_to_tweet_id=tweet["id"],
                text=msg)

    def on_exception(self, exception):
        logging.error(f'Error in Twitter plugin: {exception}')
