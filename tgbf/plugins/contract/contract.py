from tgbf.plugin import TGBFPlugin
from telegram import Update, ParseMode
from telegram.ext import CallbackContext, CommandHandler


class Contract(TGBFPlugin):

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.contract_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def contract_callback(self, update: Update, context: CallbackContext):
        contract = self.config.get("contract")
        dextools = self.config.get("dextools")
        msg = self.config.get("msg")

        update.message.reply_text(
            text=f'{msg}\n<code>{contract}</code>\n\n<a href="{dextools}">Trade on DEXTools</a>',
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True)
