import logging
import tweepy
import tgbf.emoji as emo

from tgbf.plugin import TGBFPlugin
from tgbf.lamden.connect import Connect


class Twitter(TGBFPlugin):
    client = None

    def load(self):
        if not self.global_table_exists("wallets", db_name="twitter"):
            sql = self.get_global_resource("create_wallets.sql")
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

        bot_username = f"@{self.client.get_me().data['username']}"

        streaming_client = MentionStream(self.config.get("bearer_token"), self.client, self)
        streaming_client.add_rules(tweepy.StreamRule(bot_username))
        streaming_client.filter(
            threaded=True,
            expansions=[
                "author_id",
                "in_reply_to_user_id",
                "entities.mentions.username"
            ],
            tweet_fields=[
                "author_id",
                "created_at",
                "conversation_id",
                "in_reply_to_user_id"
            ]
        )


class MentionStream(tweepy.StreamingClient):
    bot_username = None
    client = None
    plugin = None

    def __init__(self, bearer_token, client: tweepy.Client, plugin: Twitter):
        super().__init__(bearer_token)
        self.client = client
        self.plugin = plugin

        self.bot_username = f"@{self.client.get_me().data['username'].lower()}"

    def on_tweet(self, tweet):
        text = tweet.text.lower()
        text_list = text.split()

        if self.bot_username not in text_list:
            return

        success, result = self.get_command(text_list)

        from_user = tweet.author_id

        wallet = self.plugin.get_wallet(from_user, db_name="twitter")
        lamden = Connect(wallet)

        if not success:
            self.client.create_tweet(
                in_reply_to_tweet_id=tweet.id,
                text=result)
            return

        command = result[0]

        # ---- TIP ----
        if command == "tip":
            amount = result[1]
            to = result[2]

            if to.startswith("@"):
                user_id = self.get_id(tweet, to)
                to_wallet = self.plugin.get_wallet(user_id, db_name="twitter")
                to_address = to_wallet.verifying_key
            else:
                self.client.create_tweet(
                    in_reply_to_tweet_id=tweet.id,
                    text=f"{emo.ERROR} Username needs to start with @")
                return

            res = lamden.send(amount, to_address)

            if "error" in res:
                msg = f"{emo.ERROR} Transaction error: {res['error']}"
                logging.error(msg)
                self.client.create_tweet(
                    in_reply_to_tweet_id=tweet.id,
                    text=msg)
                return

            msg = f'{emo.MONEY} Tipped {amount} $TAU to {to}\n ' + \
                  f'{lamden.explorer_url}/transactions/{res["hash"]}'

            self.client.create_tweet(
                in_reply_to_tweet_id=tweet.id,
                text=msg)

        # ---- ADDRESS ----
        elif command == "address":
            user_wallet = self.plugin.get_wallet(from_user, db_name="twitter")
            user_address = user_wallet.verifying_key

            self.client.create_tweet(
                in_reply_to_tweet_id=tweet.id,
                text=f"Your #Lamden address: {user_address}")

        # ---- SEND ----
        elif command == "send":
            amount = result[1]
            to = result[2]

            if not lamden.is_address_valid(to):
                self.client.create_tweet(
                    in_reply_to_tweet_id=tweet.id,
                    text=f"{emo.ERROR} Not a valid #Lamden address")
                return

            res = lamden.send(amount, to)

            if "error" in res:
                msg = f"{emo.ERROR} Transaction error: {res['error']}"
                logging.error(msg)
                self.client.create_tweet(
                    in_reply_to_tweet_id=tweet.id,
                    text=msg)
                return

            msg = f'{emo.MONEY} Sent {amount} $TAU to {to}\n ' + \
                  f'{lamden.explorer_url}/transactions/{res["hash"]}'

            self.client.create_tweet(
                in_reply_to_tweet_id=tweet.id,
                text=msg)

        # ---- HELP ----
        elif command == "help":
            self.client.create_tweet(
                in_reply_to_tweet_id=tweet.id,
                text=self.plugin.get_usage())

    def get_command(self, text_list: list):
        try:
            for i in range(len(text_list)):
                if text_list[i] == self.bot_username:
                    if text_list[i + 1] in ["tip", "address", "send", "help"]:
                        return True, text_list[i + 1:]
            return False, f"{emo.ERROR} Unknown command"
        except:
            return False, f"{emo.ERROR} Wrong syntax"

    def get_id(self, tweet, username):
        for user in tweet.data["entities"]["mentions"]:
            u = "@" + user["username"].lower()
            if u == username.lower():
                return int(user["id"])

    def on_exception(self, exception):
        msg = f'Error in Twitter plugin: {exception}'
        self.plugin.notify(msg)
        logging.error(msg)
