import logging
import tgbf.emoji as emo

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Rtauaddliq(TGBFPlugin):

    def load(self):
        self.add_handler(CommandHandler(
            self.handle,
            self.liquidity_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def liquidity_callback(self, update: Update, context: CallbackContext):
        username = update.effective_user.username
        if username != "cross_chain1" and username != "endogen":
            update.message.reply_text(f"{emo.ERROR} You are not allowed to do that")
            return

        wallet = self.get_wallet(1)
        lamden = Connect(wallet)

        message = update.message.reply_text(f"{emo.MONEY_FACE} Adding Liquidity...")

        contract = self.config.get("contract")

        kwargs = {
            "action": "action_liquidity",
            "payload": {"function": "add_liquidity", "buy": True}
        }

        try:
            # Call contract
            distribute = lamden.post_transaction(
                stamps=2000,
                contract=contract,
                function="external_call",
                kwargs=kwargs
            )
        except Exception as e:
            logging.error(f"Error calling RTAU liquidity function: {e}")
            message.edit_text(f"{emo.ERROR} {e}")
            return

        if "error" in distribute:
            logging.error(f"Error calling RTAU liquidity function: {distribute['error']}")
            message.edit_text(f"{emo.ERROR} {distribute['error']}")
            return

        # Get transaction hash
        tx_hash = distribute["hash"]

        # Wait for transaction to be completed
        success, result = lamden.tx_succeeded(tx_hash, check_period=10, timeout=120)

        if not success:
            logging.error(f"Transaction not successful: {result}")
            msg = f"{emo.ERROR} Error calling RTAU liquidity function: {result}"
            message.edit_text(msg)
            return

        message.edit_text(f"{emo.DONE} Liquidity added")
