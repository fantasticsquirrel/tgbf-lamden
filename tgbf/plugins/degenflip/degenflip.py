import logging
import tgbf.emoji as emo

from telegram import Update, ParseMode
from telegram.ext import CommandHandler, CallbackContext
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Degenflip(TGBFPlugin):

    TOKEN_CONTRACT = "con_degen"
    TOKEN_SYMBOL = "DEGEN"

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.degenflip_callback,
            run_async=True))

    @TGBFPlugin.blacklist
    @TGBFPlugin.send_typing
    def degenflip_callback(self, update: Update, context: CallbackContext):
        if len(context.args) == 1 and context.args[0].lower() == "balance":
            contract = self.config.get("contract")

            b = Connect().get_balance(token=self.TOKEN_CONTRACT, contract=contract)
            b = b["value"] if "value" in b else 0
            b = float(str(b)) if b else float("0")
            b = f"{int(b):,}"

            update.message.reply_text(
                text=f"<code>Balance of {contract}\n{b} {self.TOKEN_SYMBOL}</code>",
                parse_mode=ParseMode.HTML
            )

            return

        if len(context.args) != 1:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        amount = context.args[0]

        try:
            amount = float(amount)

            if not amount.is_integer():
                raise ValueError

            amount = int(amount)
        except:
            # Validate amount of TAU to bet
            msg = f"{emo.ERROR} Amount (first argument) needs to be an Integer"
            update.message.reply_text(msg)
            return

        contract = self.config.get("contract")
        function = self.config.get("function")

        con_msg = f"{emo.HOURGLASS} Calling contract..."
        message = update.message.reply_text(con_msg)

        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet)

        try:
            # Check if contract is approved to spend the token
            approved = lamden.get_approved_amount(contract, token=self.TOKEN_CONTRACT)
            approved = approved["value"] if "value" in approved else 0
            approved = approved if approved is not None else 0

            msg = f"Approved amount of {self.TOKEN_SYMBOL} for {contract}: {approved}"
            logging.info(msg)

            if amount > float(approved):
                app = lamden.approve_contract(contract, token=self.TOKEN_CONTRACT)
                msg = f"Approved {contract}: {app}"
                logging.info(msg)
        except Exception as e:
            logging.error(f"Error approving degenflip contract: {e}")
            message.edit_text(f"{emo.ERROR} {e}")
            return

        try:
            # Call contract
            flip = lamden.post_transaction(
                stamps=100,
                contract=contract,
                function=function,
                kwargs={"amount": amount}
            )
        except Exception as e:
            logging.error(f"Error calling degenflip contract: {e}")
            message.edit_text(f"{emo.ERROR} {e}")
            return

        logging.info(f"Executed degenflip contract: {flip}")

        if "error" in flip:
            logging.error(f"Degenflip contract returned error: {flip['error']}")
            message.edit_text(f"{emo.ERROR} {flip['error']}")
            return

        # Get transaction hash
        tx_hash = flip["hash"]

        # Wait for transaction to be completed
        success, result = lamden.tx_succeeded(tx_hash)

        if not success:
            logging.error(f"Degenflip transaction not successful: {result}")
            message.edit_text(f"{emo.ERROR} {result}")
            return

        ex_link = f'<a href="{lamden.explorer_url}/transactions/{tx_hash}">View Transaction on Explorer</a>'

        degen_amount = result["result"][result["result"].find("'") + 1:result["result"].rfind("'")]
        degen_amount = int(float(degen_amount))

        if degen_amount != 0:
            logging.info(f"User WON <code>{degen_amount - amount}</code> {self.TOKEN_SYMBOL}")
            msg = f"YOU WON <code>{degen_amount - amount}</code> {self.TOKEN_SYMBOL} {emo.MONEY_FACE}"
        else:
            logging.info(f"User LOST {amount} {self.TOKEN_SYMBOL}")
            msg = f"You lost <code>{amount:,}</code> {self.TOKEN_SYMBOL} {emo.SAD} better luck next time"

        message.edit_text(
            f"{msg}\n{ex_link}",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True)
