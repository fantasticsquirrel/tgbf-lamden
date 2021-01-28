from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from tgbf.plugin import TGBFPlugin


class Balance(TGBFPlugin):

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.balance_callback,
            run_async=True),
            group=1)

    def balance_callback(self, update: Update, context: CallbackContext):
        print("BALANCE")  # TODO: Remove
