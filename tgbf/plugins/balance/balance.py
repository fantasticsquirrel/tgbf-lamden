import tgbf.emoji as emo

from telegram import Update
from lamden.crypto.wallet import Wallet
from tgbf.lamden.connect import Connect
from telegram.ext import CommandHandler, CallbackContext
from telegram import ParseMode
from tgbf.plugin import TGBFPlugin


class Balance(TGBFPlugin):

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.balance_callback,
            run_async=True),
            group=1)

    @TGBFPlugin.send_typing
    def balance_callback(self, update: Update, context: CallbackContext):
        sql = self.get_resource("select_wallet.sql", plugin="wallets")
        res = self.execute_sql(sql, update.effective_user.id, plugin="wallets")

        if not res["data"]:
            msg = f"{emo.ERROR} Can't retrieve your wallet"
            update.message.reply_text(msg)
            self.notify(msg)
            return

        wallet = Wallet(res["data"][0][2])
        lamden = Connect(wallet=wallet)

        balance = lamden.get_balance(wallet.verifying_key)
        balance = balance["value"] if "value" in balance else 0

        update.message.reply_text(
            text=f"`{balance} TAU`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
