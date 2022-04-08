from telegram import Update, ParseMode
from telegram.ext import CommandHandler, CallbackContext
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Rtautotalsupply(TGBFPlugin):

    def load(self):
        self.add_handler(CommandHandler(
            self.handle,
            self.total_supply_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def total_supply_callback(self, update: Update, context: CallbackContext):
        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet)

        total_supply = lamden.get_contract_variable(
                self.config.get("contract"),
                "total_supply")

        total_supply = total_supply["value"] if "value" in total_supply else 0
        total_supply = float(str(total_supply)) if total_supply else float("0")

        if total_supply:
            total_supply = int(total_supply)
        else:
            total_supply = 0

        update.message.reply_text(
            f'<code>{total_supply:,}</code> Total Supply',
            parse_mode=ParseMode.HTML)
