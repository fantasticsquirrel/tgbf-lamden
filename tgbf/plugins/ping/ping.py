from tgbf.plugin import TGBFPlugin
from telegram import Update
from telegram.ext import CallbackContext, CommandHandler


class Ping(TGBFPlugin):

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.ping_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def ping_callback(self, update: Update, context: CallbackContext):
        context.bot.send_message(134166731, f"pong {context.args[0]}")
