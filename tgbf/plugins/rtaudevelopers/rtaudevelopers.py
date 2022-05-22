from telegram import Update, ParseMode
from telegram.ext import CommandHandler, CallbackContext
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Rtaudevelopers(TGBFPlugin):

    def load(self):
        self.add_handler(CommandHandler(
            self.handle,
            self.developers_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def developers_callback(self, update: Update, context: CallbackContext):
        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet)

        tau_pool = lamden.get_contract_variable(
                "currency",
                "balances",
                self.config.get("contract"))

        tau_pool = tau_pool["value"] if "value" in tau_pool else 0
        tau_pool = float(str(tau_pool)) if tau_pool else float("0")

        if tau_pool:
            tau_pool = int(tau_pool)
        else:
            tau_pool = 0

        update.message.reply_text(
            f'<code>{tau_pool:,}</code> TAU in Dev-Pool',
            parse_mode=ParseMode.HTML)