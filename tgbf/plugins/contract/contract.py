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
        pancake = self.config.get("pancake")
        how_to = self.config.get("how_to")
        msg_start = self.config.get("msg_start")
        msg_end = self.config.get("msg_end")

        update.message.reply_text(
            f'{msg_start}\n\n'
            f'<code>{contract}</code>\n\n'
            f'<a href="{dextools}">DEXTools</a> | '
            f'<a href="{pancake}">PancakeSwap</a> | '
            f'<a href="{how_to}">How-To</a>\n\n'
            f'{msg_end}',
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True)
