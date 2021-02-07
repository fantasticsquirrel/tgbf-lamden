from tgbf.plugin import TGBFPlugin
from telegram import Update, ParseMode
from telegram.ext import CallbackContext, CommandHandler


class Start(TGBFPlugin):

    START_FILE = "start.md"

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.start_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def start_callback(self, update: Update, context: CallbackContext):
        wallet = self.get_wallet(update.effective_user.id)

        start = self.get_resource(self.START_FILE)
        start = start.replace("{{address}}", wallet.verifying_key)

        update.message.reply_text(
            start,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True)
