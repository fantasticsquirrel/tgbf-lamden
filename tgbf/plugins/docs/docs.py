from tgbf.plugin import TGBFPlugin
from telegram import Update
from telegram.ext import CallbackContext, CommandHandler


class Docs(TGBFPlugin):

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.docs_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def docs_callback(self, update: Update, context: CallbackContext):
        update.message.reply_text(text="https://t.me/lamden_community_docs")
