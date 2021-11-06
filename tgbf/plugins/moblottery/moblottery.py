import os
import logging
import tgbf.emoji as emo

from telegram import Update, ParseMode
from telegram.ext import CommandHandler, CallbackContext
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Moblottery(TGBFPlugin):

    TOKEN_CONTRACT = "con_mintorburn"

    def load(self):
        self.add_handler(CommandHandler(
            self.handle,
            self.collidertau_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def collidertau_callback(self, update: Update, context: CallbackContext):
        contract = self.config.get("contract")

        if len(context.args) == 0 or len(context.args) > 1:
            con = Connect()

            ent = con.get_contract_variable(contract=contract, variable="entry_amount")
            ent = ent["value"] if "value" in ent else 0

            pot = con.get_contract_variable(contract=contract, variable="pot_amount")
            pot = pot["value"] if "value" in pot else 0

            replace = {
                "{{entry_amount}}": str(ent),
                "{{pot_amount}}": str(pot)
            }

            update.message.reply_text(
                self.get_usage(replace),
                parse_mode=ParseMode.HTML)
            return

        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet)

        # JOIN LOTTERY
        if context.args[0].lower() == "buy":
            msg = f"{emo.HOURGLASS} Buying lottery ticket..."
            message = update.message.reply_text(msg)

            try:
                # Check if contract is approved to spend the token
                approved = lamden.get_approved_amount(contract, token=self.TOKEN_CONTRACT)
                approved = approved["value"] if "value" in approved else 0
                approved = approved if approved is not None else 0

                msg = f"Approved amount of MOB for {contract}: {approved}"
                logging.info(msg)

                if float(approved) == 0:
                    app = lamden.approve_contract(contract, token=self.TOKEN_CONTRACT)
                    msg = f"Approved {contract}: {app}"
                    logging.info(msg)
            except Exception as e:
                logging.error(f"Error approving moblottery contract: {e}")
                message.edit_text(f"{emo.ERROR} {e}")
                return

            try:
                # Call contract
                join = lamden.post_transaction(
                    stamps=120,
                    contract=contract,
                    function="joinLottery",
                    kwargs={}
                )
            except Exception as e:
                logging.error(f"Error calling moblottery contract: {e}")
                message.edit_text(f"{emo.ERROR} {e}")
                return

            logging.info(f"Executed moblottery contract: {join}")

            if "error" in join:
                logging.error(f"Moblottery contract returned error: {join['error']}")
                message.edit_text(f"{emo.ERROR} {join['error']}")
                return

            # Get transaction hash
            tx_hash = join["hash"]

            # Wait for transaction to be completed
            success, result = lamden.tx_succeeded(tx_hash)

            if not success:
                logging.error(f"Boblottery transaction not successful: {result}")
                message.edit_text(f"{emo.ERROR} {result}")
                return

            message.edit_text(f"{emo.DONE} You just bought one entry for the MOB Weekly Lottery")

        # DRAW WINNER
        elif context.args[0].lower() == "finish":
            msg = f"{emo.HOURGLASS} Drawing winner..."
            message = update.message.reply_text(msg)

            pot = Connect().get_contract_variable(contract=contract, variable="pot_amount")
            pot = pot["value"] if "value" in pot else 0
            pot = float(str(pot)) if pot else float("0")
            pot = f"{int(pot):,}"

            try:
                # Call contract
                join = lamden.post_transaction(
                    stamps=100,
                    contract=contract,
                    function="finishLottery",
                    kwargs={}
                )
            except Exception as e:
                logging.error(f"Error calling moblottery contract: {e}")
                message.edit_text(f"{emo.ERROR} {e}")
                return

            logging.info(f"Executed moblottery contract: {join}")

            if "error" in join:
                logging.error(f"Moblottery contract returned error: {join['error']}")
                message.edit_text(f"{emo.ERROR} {join['error']}")
                return

            # Get transaction hash
            tx_hash = join["hash"]

            # Wait for transaction to be completed
            success, result = lamden.tx_succeeded(tx_hash)

            if not success:
                logging.error(f"Boblottery transaction not successful: {result}")
                message.edit_text(f"{emo.ERROR} {result}")
                return

            winner = result["result"].replace("'", "")
            logging.info(f"Address <code>{winner}</code> won the MOB lottery!")

            winner = f"{winner[0:4]}...{winner[-4:len(winner)]}"
            tx_url = f'<a href="{lamden.explorer_url}/transactions/{tx_hash}">{winner}</a>'

            message.edit_text(f"{emo.MONEY_FACE} Address {tx_url} won {pot} MOB!!")
