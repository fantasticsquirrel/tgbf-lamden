from tgbf.plugin import TGBFPlugin
from telegram import Update, ParseMode
from telegram.ext import CallbackContext, CommandHandler


class Slippage(TGBFPlugin):

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.slippage_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def slippage_callback(self, update: Update, context: CallbackContext):
        update.message.reply_text(
            text=f'{self.config.get("text")}',
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False)
