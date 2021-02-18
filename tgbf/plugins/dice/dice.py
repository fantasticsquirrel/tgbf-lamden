import tgbf.emoji as emo

from telegram import Update, ParseMode
from telegram.ext import CommandHandler, CallbackContext
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Dice(TGBFPlugin):

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.dice_callback,
            run_async=True))

    def dice_callback(self, update: Update, context: CallbackContext):
        if len(context.args) != 2:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        # TODO: Add validations
        amount = context.args[0]
        number = context.args[1]

        wallet = self.get_wallet(update.effective_user.id)
        lamden = Connect(wallet)

        roll = lamden.post_transaction(500, "con_dice", "roll", {})

        success, result = lamden.tx_succeeded(roll["hash"])

        if not success:
            update.message.reply_text(f"{emo.ERROR} {result}")
            return

        # TODO: Show link to transaction
        result = result["result"]
        update.message.reply_text(f"Result: {result}")
