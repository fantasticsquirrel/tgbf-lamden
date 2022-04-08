from telegram import Update, ParseMode
from telegram.ext import CommandHandler, CallbackContext
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Rtaucircsupply(TGBFPlugin):

    def load(self):
        self.add_handler(CommandHandler(
            self.handle,
            self.circ_supply_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def circ_supply_callback(self, update: Update, context: CallbackContext):
        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet)

        total_supply = lamden.get_contract_variable(
                self.config.get("contract"),
                "total_supply")

        total_supply = total_supply["value"] if "value" in total_supply else 0
        total_supply = float(str(total_supply)) if total_supply else float("0")

        burn_balance = lamden.get_contract_variable(
                self.config.get("contract"),
                "balances",
                "reflecttau_burn_address")

        burn_balance = burn_balance["value"] if "value" in burn_balance else 0
        burn_balance = float(str(burn_balance)) if burn_balance else float("0")

        reflection_balance = lamden.get_contract_variable(
                self.config.get("contract"),
                "balances",
                "con_reflecttau_v2_reflection")

        reflection_balance = reflection_balance["value"] if "value" in reflection_balance else 0
        reflection_balance = float(str(reflection_balance)) if reflection_balance else float("0")

        circ_suppy = total_supply - burn_balance - reflection_balance

        if circ_suppy:
            circ_suppy = int(circ_suppy)
        else:
            circ_suppy = 0

        update.message.reply_text(
            f'<code>{circ_suppy:,}</code> Circulating Supply',
            parse_mode=ParseMode.HTML)
