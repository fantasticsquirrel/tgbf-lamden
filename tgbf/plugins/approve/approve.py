import logging
import tgbf.emoji as emo

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from telegram.utils.helpers import escape_markdown as esc_mk
from telegram import ParseMode

from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Approve(TGBFPlugin):

    def load(self):
        if not self.table_exists("approved"):
            sql = self.get_resource("create_approved.sql")
            self.execute_sql(sql)

        self.add_handler(CommandHandler(
            self.name,
            self.approve_callback,
            run_async=True))

    @TGBFPlugin.private
    @TGBFPlugin.send_typing
    def approve_callback(self, update: Update, context: CallbackContext):
        wallet = self.get_wallet(update.effective_user.id)
        lamden = Connect(wallet=wallet)

        # If no arguments, show how to use
        if not context.args:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        # If more than 2 arguments, show how to use
        if len(context.args) > 2:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        # If argument is 'list' show all approved contracts
        if len(context.args) == 1 and context.args[0].lower() == "list":
            approved = self.execute_sql(
                self.get_resource("select_approved.sql"),
                wallet.verifying_key)

            if not approved["data"]:
                update.message.reply_text("No approved contracts found")
                return

            msg = str("Approved Contracts\n\n")
            for a in approved["data"]:
                contract = a[0]

                amount = lamden.get_approved_amount(contract)
                amount = amount["value"] if "value" in amount else 0
                amount = amount if amount is not None else 0

                if float(amount).is_integer():
                    amount = int(amount)

                msg += f"{contract} -> {amount} TAU\n"

            update.message.reply_text(
                "`" + esc_mk(msg, version=2) + "`",
                parse_mode=ParseMode.MARKDOWN_V2)

            return

        contract = context.args[0]
        amount = context.args[1]

        try:
            amount = float(amount)
        except:
            msg = f"{emo.ERROR} Amount (second argument) is not valid"
            update.message.reply_text(msg)
            return

        msg = f"{emo.HOURGLASS} Approving contract"
        message = update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)

        try:
            # Approve contract
            result = lamden.approve_contract(contract, amount)
        except Exception as e:
            msg = f"Could not send transaction: {e}"
            message.edit_text(f"{emo.ERROR} {e}")
            logging.error(msg)
            self.notify(msg)
            return

        if "error" in result:
            logging.error(f"Transaction replied error: {result['error']}")
            message.edit_text(f"{emo.ERROR} {result['error']}")
            return

        # Get transaction hash
        tx_hash = result["hash"]

        success, result = lamden.tx_succeeded(tx_hash)

        if not success:
            logging.error(f"Transaction not successful: {result}")
            message.edit_text(f"{emo.ERROR} {result}")
            return

        # Insert details into database
        self.execute_sql(
            self.get_resource("insert_approved.sql"),
            wallet.verifying_key,
            contract,
            amount,
            tx_hash)

        ex_url = f"{lamden.explorer_url}/transactions/{tx_hash}"

        message.edit_text(
            f"{emo.DONE} [Contract approved]({ex_url})",
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True)
