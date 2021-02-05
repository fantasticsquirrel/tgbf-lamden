import logging

from telegram import Update
from tgbf.plugin import TGBFPlugin
from lamden.crypto.wallet import Wallet
from telegram.ext import MessageHandler, Filters, CallbackContext


class Wallets(TGBFPlugin):

    def load(self):
        if not self.table_exists("wallets"):
            sql = self.get_resource("create_wallets.sql")
            self.execute_sql(sql)

        # Capture all executed commands
        self.add_handler(MessageHandler(
            Filters.command,
            self.wallet_callback),
            group=0)

    def wallet_callback(self, update: Update, context: CallbackContext):
        try:
            user = update.effective_user

            if not user or not user.id:
                msg = f"Could not extract user for wallet creation: {update}"
                logging.warning(msg)
                self.notify(msg)
                return

            # Check if user already has a wallet
            sql = self.get_resource("select_wallets.sql")
            res = self.execute_sql(sql, user.id)

            # User already has wallet
            if res["data"]:
                return

            # Create wallet
            wallet = Wallet()

            # Save wallet to database
            self.execute_sql(
                self.get_resource("insert_wallets.sql"),
                user.id,
                wallet.verifying_key,
                wallet.signing_key)

            logging.info(f"Wallet created for {user}: {wallet.verifying_key} - {wallet.signing_key}")
        except Exception as e:
            msg = f"Could not create wallet: {e}"
            logging.error(f"{msg} - {update}")
            self.notify(msg)
