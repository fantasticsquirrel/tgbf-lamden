import logging

from tgbf.plugin import TGBFPlugin
from telegram import Update, ParseMode
from tgbf.lamden.wallet import LamdenWallet
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
        sql = self.get_resource("select_wallet.sql", plugin="wallet")
        res = self.execute_sql(sql, update.effective_user.id, plugin="wallet")

        if not res["data"]:
            # Get user info
            user = update.effective_user

            # Create wallet
            wallet = LamdenWallet()
            address = wallet.address

            # Save wallet info to database
            sql = self.get_resource("insert_wallet.sql", plugin="wallet")
            self.execute_sql(sql, user.id, wallet.address, wallet.privkey, plugin="wallet")

            logging.info(f"Wallet created for {user}: A: {wallet.address} - P: {wallet.privkey}")
        else:
            address = res["data"][0][1]

        start = self.get_resource(self.START_FILE)
        start = start.replace("{{address}}", address)

        update.message.reply_text(
            start,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True)
