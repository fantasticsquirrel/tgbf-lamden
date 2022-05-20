import logging
import tgbf.emoji as emo

from telegram import Update, ParseMode
from telegram.ext import CommandHandler, CallbackContext
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Minemit(TGBFPlugin):

    def load(self):
        self.add_handler(CommandHandler(
            self.handle,
            self.minemit_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def minemit_callback(self, update: Update, context: CallbackContext):
        if len(context.args) != 1:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        number = context.args[0]

        try:
            number = float(number)
        except:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        if not number.is_integer():
            msg = f"{emo.ERROR} First argument needs to be an Integer"
            update.message.reply_text(msg)
            return

        number = int(number)

        message = update.message.reply_text(f'Mining MIT {number} times...')

        contract = self.config.get("contract")
        function = self.config.get("function")

        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet)

        try:
            mine = lamden.post_transaction(
                stamps=1000,
                contract=contract,
                function=function,
                kwargs={"times": number})
        except Exception as e:
            logging.error(f"Error calling {contract} contract: {e}")
            message.edit_text(f"{emo.ERROR} {e}")
            return

        if "error" in mine:
            logging.error(f"{contract} contract returned error: {mine['error']}")
            message.edit_text(f"{emo.ERROR} {mine['error']}")
            return

        # Get transaction hash
        tx_hash = mine["hash"]

        # Wait for transaction to be completed
        success, result = lamden.tx_succeeded(tx_hash)

        if not success:
            logging.error(f"Transaction not successful: {result}")
            message.edit_text(f"{emo.ERROR} {result}")
            return

        message.edit_text(f"{emo.DONE} Done")
