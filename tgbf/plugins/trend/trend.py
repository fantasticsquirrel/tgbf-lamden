from telegram import Update
from tgbf.plugin import TGBFPlugin
from telegram.ext import CommandHandler, CallbackContext


class Trend(TGBFPlugin):

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.trend_callback,
            run_async=True))

    def trend_callback(self, update: Update, context: CallbackContext):
        pass
