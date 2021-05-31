from tgbf.plugin import TGBFPlugin
from telegram import Update
from telegram.ext import CallbackContext, CommandHandler


class Connect(TGBFPlugin):

    def load(self):
        self.add_handler(CommandHandler(
            self.handle,
            self.connect_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def connect_callback(self, update: Update, context: CallbackContext):
        update.message.reply_text("https://link.medium.com/QqdOVOhmHgb")
