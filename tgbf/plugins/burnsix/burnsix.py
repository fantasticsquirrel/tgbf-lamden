import logging
import tgbf.emoji as emo

from tgbf.plugin import TGBFPlugin
from tgbf.lamden.connect import Connect
from telegram.ext import CommandHandler, CallbackContext
from telegram import Update, ParseMode


class Burnsix(TGBFPlugin):

    SIXSIXSIX_CONTRACT = "con_demoncoin"

    def load(self):
        self.add_handler(CommandHandler(
            self.handle,
            self.burn_callback,
            run_async=True))

    @TGBFPlugin.private
    @TGBFPlugin.send_typing
    def burn_callback(self, update: Update, context: CallbackContext):
        if len(context.args) != 1:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet=wallet)

        amount = context.args[0]

        try:
            # Check if amount is valid
            amount = float(amount)
        except:
            msg = f"{emo.ERROR} Amount not valid"
            update.message.reply_text(msg)
            return

        if amount.is_integer():
            amount = int(amount)

        # --- TEMP ---
        # TODO: Remove temporal fix
        amount = int(amount)
        if amount == 0:
            msg = f"{emo.ERROR} Amount needs to be an Integer"
            update.message.reply_text(msg)
            return
        # --- TEMP ---

        contract = self.config.get("contract")
        function = self.config.get("function")

        msg = f"{emo.HOURGLASS} Burning 666 and redeeming LIGHT..."
        message = update.message.reply_text(msg)

        try:
            # Check if contract is approved to spend the token
            approved = lamden.get_approved_amount(contract, token=self.SIXSIXSIX_CONTRACT)
            approved = approved["value"] if "value" in approved else 0
            approved = approved if approved is not None else 0

            msg = f"Approved amount of SIXSIXSIX for {contract}: {approved}"
            logging.info(msg)

            if amount > float(approved):
                app = lamden.approve_contract(contract, token=self.SIXSIXSIX_CONTRACT)
                msg = f"Approved {contract}: {app}"
                logging.info(msg)
        except Exception as e:
            logging.error(f"Error approving banish contract: {e}")
            message.edit_text(f"{emo.ERROR} {e}")
            return


        try:
            # Burn SIXSIXSIX token and redeem LIGHT token
            burn = lamden.post_transaction(
                100,
                contract,
                function,
                {"amount": amount}
            )
        except Exception as e:
            msg = f"Could not send transaction: {e}"
            message.edit_text(f"{emo.ERROR} {e}")
            logging.error(msg)
            self.notify(msg)
            return

        logging.info(f"Burned {amount} SIXSIXSIX: {burn}")

        if "error" in burn:
            msg = f"Transaction replied error: {burn['error']}"
            message.edit_text(f"{emo.ERROR} {burn['error']}")
            logging.error(msg)
            return

        # Get transaction hash
        tx_hash = burn["hash"]

        link = f'<a href="{lamden.explorer_url}/transactions/{tx_hash}">View Transaction on Explorer</a>'

        rate = lamden.get_contract_variable(contract, "metadata", key="rate")["value"]
        light_amount = int(float(rate) * amount)

        message.edit_text(
            f"{emo.STARS} Redeemed <code>{light_amount}</code> LIGHT\n"
            f"{emo.FIRE} Burned <code>{amount}</code> SIXSIXSIX\n{link}",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True)
