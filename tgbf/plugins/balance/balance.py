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

        b = lamden.get_balance(wallet.verifying_key)
        b = b["value"] if "value" in b else 0
        b = str(b) if b else "0"

        b = str(int(b)) if float(b).is_integer() else "{:.2f}".format(float(b))

        update.message.reply_text(
            text=f"`{b} TAU`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
