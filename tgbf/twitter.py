import logging
import os.path
import sqlite3
from pathlib import Path

import tweepy
import time
import json

import tgbf.constants as c
from lamden.crypto.wallet import Wallet


class TwitterBot:
    client = None

    def __init__(self, consumer_key: str, consumer_sec: str, access_token_key: str, access_token_sec: str):
        self.client = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_sec,
            access_token=access_token_key,
            access_token_secret=access_token_sec
        )

        stream = ReplyStream(consumer_key, consumer_sec, access_token_key, access_token_sec, self.client)
        stream.filter(track=[f"@{self.client.get_me().data['username']}"], threaded=True)

        while True:
            time.sleep(0.01)

    def update_status(self, message: str):
        self.client.create_tweet(text=message)


class ReplyStream(tweepy.Stream):
    client = None

    def __init__(self, consumer_key, consumer_sec, access_token_key, access_token_sec, client):
        super().__init__(consumer_key, consumer_sec, access_token_key, access_token_sec)
        self.client = client

    def on_data(self, raw_data):
        data = json.loads(raw_data)
        logging.debug(f'ReplyStream - on_data()', data)

        user = data["user"]["screen_name"]

        wallet = get_wallet(user)
        print("wallet - address", wallet.verifying_key)
        print("wallet - privkey", wallet.signing_key)

        text = data["text"].lower()
        text_list = text.split()

        if text_list[1] == "tip":
            amount = text_list[2]
            to = text_list[3]
            self.client.create_tweet(text=f"Hey @{user} i just tipped {to} with {amount} TAU")

    def on_exception(self, exception):
        logging.error(f'Error in Twitter Bot: {exception}')


def get_wallet(username):
    """ Return address and privkey for given Twitter username.
    If no wallet exists then it will be created. """

    path, _ = os.path.split(os.getcwd())
    db_file = os.path.join(path, c.DIR_DAT, "twitter.db")

    if not db_table_exists(db_file, "tw_wallets"):
        sql = os.path.join(path, c.DIR_RES, "table_exists.sql")
        res = db(db_file, sql, username)

    sql = os.path.join(path, c.DIR_RES, "select_tw_wallet.sql")

    res = db(db_file, sql, username)

    # User already has a wallet
    if res["data"]:
        return Wallet(res["data"][0][2])

    # Create new wallet
    wallet = Wallet()

    sql = os.path.join(path, c.DIR_RES, "insert_tw_wallet.sql")

    # Save wallet to database
    db(
        db_file,
        sql,
        username,
        wallet.verifying_key,
        wallet.signing_key)

    logging.info(f"Twitter Wallet created for {username}: {wallet.verifying_key} / {wallet.signing_key}")
    return wallet


def db(db_path, sql, *args):
    """ Open database connection and execute SQL statement """

    res = {"success": None, "data": None}

    try:
        # Create directory if it doesn't exist
        directory = os.path.dirname(db_path)
        os.makedirs(directory, exist_ok=True)
    except Exception as e:
        res["data"] = str(e)
        res["success"] = False
        logging.error(e)

    with sqlite3.connect(db_path, timeout=5) as con:
        try:
            cur = con.cursor()
            cur.execute(sql, args)
            con.commit()

            res["data"] = cur.fetchall()
            res["success"] = True

        except Exception as e:
            res["data"] = str(e)
            res["success"] = False
            logging.error(e)

        return res


def db_table_exists(db_path, table_name):
    """ Open connection to database and check if given table exists """

    if not Path(db_path).is_file():
        return False

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    exists = False

    path, _ = os.path.split(os.getcwd())
    sql = os.path.join(path, c.DIR_RES, "table_exists.sql")

    try:
        if cur.execute(sql, [table_name]).fetchone():
            exists = True
    except Exception as e:
        logging.error(e)

    con.close()
    return exists

if __name__ == "__main__":
    twitter = TwitterBot(
        "TJ7Y0y927hwefSDTNEhyyMhbE",
        "c2sxEg9AY3xAWV4hpA5s13vtxEfZYWPboetsgB4Y9Y9sSzegzO",
        "1031526641028288513-3LzOWL7fvxN97Iyn57Q4CrGVCkf9VH",
        "36MPjgSeIDfMKw8061BS8zQMnO7JETkdF6oDGL1H9E3L3")

    while True:
        time.sleep(0.01)
