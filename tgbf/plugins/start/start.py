import logging

from tgbf.plugin import TGBFPlugin
from telegram import Update, ParseMode
from lamden.crypto.wallet import Wallet
from telegram.ext import CallbackContext, CommandHandler


class Start(TGBFPlugin):

    START_FILE = "start.md"

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.start_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def start_callback(self, update: Update, context: CallbackContext):
        sql = self.get_resource("select_wallet.sql", plugin="wallets")
        res = self.execute_sql(sql, update.effective_user.id, plugin="wallets")

        if not res["data"]:
            # Get user info
            user = update.effective_user

            # Create wallet
            wallet = Wallet()
            address = wallet.verifying_key

            # Save wallet to database
            self.execute_sql(
                self.get_resource("insert_wallet.sql", plugin="wallets"),
                user.id,
                wallet.verifying_key,
                wallet.signing_key,
                plugin="wallets")

            logging.info(f"Wallet created for {user}: {wallet.verifying_key} - {wallet.signing_key}")
        else:
            address = res["data"][0][1]

        start = self.get_resource(self.START_FILE)
        start = start.replace("{{address}}", address)

        update.message.reply_text(
            start,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True)
