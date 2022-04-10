import logging
import tgbf.emoji as emo

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Arb(TGBFPlugin):

    def load(self):
        self.add_handler(CommandHandler(
            self.handle,
            self.arb_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def arb_callback(self, update: Update, context: CallbackContext):
        if len(context.args) != 1:
            update.message.edit_text(f"{emo.ERROR} Number of arguments != 1")
            return

        contract = self.config.get("contract")
        tau_amount = int(context.args[0])

        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet)

        message = update.message.reply_text(f"{emo.MONEY_FACE} Arbitraging RTAU...")

        try:
            # Call contract
            arb = lamden.post_transaction(
                stamps=100,
                contract=contract,
                function="get_lp",
                kwargs={"tau_amount": tau_amount}
            )
        except Exception as e:
            logging.error(f"Error calling RTAU arbitrage function: {e}")
            message.edit_text(f"{emo.ERROR} {e}")
            return

        if "error" in arb:
            logging.error(f"Error calling RTAU arbitrage function: {arb['error']}")
            message.edit_text(f"{emo.ERROR} {arb['error']}")
            return

        # Get transaction hash
        tx_hash = arb["hash"]

        # Wait for transaction to be completed
        success, result = lamden.tx_succeeded(tx_hash)

        if not success:
            logging.error(f"Transaction not successful: {result}")
            msg = f"{emo.ERROR} Error calling RTAU arbitrage function: {result}"
            message.edit_text(msg)
            return

        message.edit_text(f"{emo.DONE} {result['result']}")
