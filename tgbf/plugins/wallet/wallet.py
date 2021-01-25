import logging

from tgbf.plugin import TGBFPlugin
from telegram.ext import MessageHandler, Filters
from lamdenpy.wallet import Wallet as LamdenWallet


class Wallet(TGBFPlugin):

    def load(self):
        if not self.table_exists("wallet"):
            sql = self.get_resource("create_wallet.sql")
            self.execute_sql(sql)

        # Capture all executed commands
        self.add_handler(MessageHandler(
            Filters.command,
            self.wallet_callback),
            group=0)

    def wallet_callback(self, update, context):
        try:
            user = update.effective_user

            if not user or not user.id:
                msg = f"Could not extract user for wallet creation: {update}"
                logging.warning(msg)
                self.notify(msg)
                return

            # Check if user already has a wallet
            sql = self.get_resource("select_wallet.sql")
            res = self.execute_sql(sql, user.id)

            # User already has wallet
            if res["data"]:
               return

            # Create wallet
            wallet = LamdenWallet()

            address = wallet.vk.encode().hex()
            privkey = wallet.sk.__bytes__()

            logging.info(f"Wallet created for {user}: A: {address} - P: {privkey}")

            # Save wallet info to database
            sql = self.get_resource("insert_wallet.sql")
            self.execute_sql(sql, user.id, address, privkey)
        except Exception as e:
            msg = f"Could not create wallet: {e}"
            logging.error(f"{msg} - {update}")
            self.notify(msg)
