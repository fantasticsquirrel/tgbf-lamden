from telegram import Update
from tgbf.lamden.connect import Connect
from telegram.ext import CommandHandler, CallbackContext
from telegram import ParseMode
from tgbf.plugin import TGBFPlugin


class Balance(TGBFPlugin):

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.balance_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def balance_callback(self, update: Update, context: CallbackContext):
        wallet = self.get_wallet(update.effective_user.id)
        lamden = Connect(wallet=wallet)

        balance = lamden.get_balance(wallet.verifying_key)
        balance = balance["value"] if "value" in balance else 0

        update.message.reply_text(
            text=f"`{balance} TAU`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
