import logging
import tgbf.emoji as emo

from tgbf.plugin import TGBFPlugin
from tgbf.lamden.connect import Connect
from telegram.ext import CommandHandler, CallbackContext
from telegram import Update, ParseMode


class Send(TGBFPlugin):

    def load(self):
        if not self.table_exists("send"):
            sql = self.get_resource("create_send.sql")
            self.execute_sql(sql)

        self.add_handler(CommandHandler(
            self.name,
            self.send_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def send_callback(self, update: Update, context: CallbackContext):
        if len(context.args) != 3:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        from_wallet = self.get_wallet(update.effective_user.id)
        lamden = Connect(wallet=from_wallet)

        token_name = context.args[0].upper()
        amount = context.args[1]

        if token_name == "TAU":
            token_contract = "currency"
        else:
            sql = self.get_resource("select_contract.sql", plugin="tokens")
            res = self.execute_sql(sql, token_name, plugin="tokens")

            if res and res["data"] and res["data"][0]:
                token_contract = res["data"][0][0]
            else:
                msg = f"{emo.ERROR} Unknown token"
                update.message.reply_text(msg)
                return

        try:
            # Check if amount is valid
            amount = float(amount)
        except:
            msg = f"{emo.ERROR} Amount not valid"
            update.message.reply_text(msg)
            return

        if amount.is_integer():
            amount = int(amount)

        to_address = context.args[2]

        if not lamden.is_address_valid(to_address):
            msg = f"{emo.ERROR} Address not valid"
            update.message.reply_text(msg)
            return

        message = update.message.reply_text(f"{emo.HOURGLASS} Sending {token_name}...")

        try:
            # Send token
            send = lamden.send(amount, to_address, token=token_contract)
        except Exception as e:
            msg = f"Could not send transaction: {e}"
            message.edit_text(f"{emo.ERROR} {e}")
            logging.error(msg)
            self.notify(msg)
            return

        if "error" in send:
            msg = f"Transaction replied error: {send['error']}"
            message.edit_text(f"{emo.ERROR} {send['error']}")
            logging.error(msg)
            return

        # Get transaction hash
        tx_hash = send["hash"]

        logging.info(f"Sent {amount} {token_name} from {from_wallet.verifying_key} to {to_address}: {send}")

        link = f'<a href="{lamden.explorer_url}/transactions/{tx_hash}">View Transaction on Explorer</a>'

        message.edit_text(
            f"{emo.MONEY} Sent <code>{amount}</code> {token_name}\n{link}",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True)

        # Wait for transaction to be completed
        success, result = lamden.tx_succeeded(tx_hash)

        if not success:
            logging.error(f"Transaction not successful: {result}")

            link = f'<a href="{lamden.explorer_url}/transactions/{tx_hash}">TRANSACTION FAILED</a>'

            message.edit_text(
                f"{emo.STOP} <del>Sent</del> <code>{amount}</code> {token_name}\n{link}",
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True)
            return

        """
        # Insert details into database
        self.execute_sql(
            self.get_resource("insert_send.sql"),
            from_wallet.verifying_key,
            to_address,
            amount,
            tx_hash)
        """
