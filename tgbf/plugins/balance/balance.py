import tgbf.emoji as emo

from telegram import Update
from tgbf.lamden.wallet import LamdenWallet
from tgbf.lamden.connect import LamdenConnect, Chain
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

    def balance_callback(self, update: Update, context: CallbackContext):
        sql = self.get_resource("select_wallet.sql", plugin="wallet")
        res = self.execute_sql(sql, update.effective_user.id, plugin="wallet")

        if not res["data"]:
            msg = f"{emo.ERROR} Can't retrieve your wallet"
            update.message.reply_text(msg)
            self.notify(msg)

        wallet = LamdenWallet(res["data"][0][2])
        lamden = LamdenConnect(chain=Chain.TEST, wallet=wallet)  # TODO: Remove TESTNET

        update.message.reply_text(
            text=f"`{lamden.get_balance(wallet.address)}` TAU",
            parse_mode=ParseMode.MARKDOWN_V2
        )
