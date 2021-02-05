import tgbf.emoji as emo

from telegram import Update
from lamden.crypto.wallet import Wallet
from tgbf.lamden.connect import Connect
from telegram.ext import CommandHandler, CallbackContext
from telegram import ParseMode
from tgbf.plugin import TGBFPlugin


class Address(TGBFPlugin):

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.address_callback,
            run_async=True),
            group=1)

    def address_callback(self, update: Update, context: CallbackContext):
        sql = self.get_resource("select_wallets.sql", plugin="wallets")
        res = self.execute_sql(sql, update.effective_user.id, plugin="wallets")

        if not res["data"]:
            msg = f"{emo.ERROR} Can't retrieve your wallet"
            update.message.reply_text(msg)
            self.notify(msg)
            return

        address = res["data"][0][2]

        # TODO: Show QR-Code too and add button to show privkey
        update.message.reply_text(
            text=f"`{address}`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
