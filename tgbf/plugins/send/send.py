import logging
import tgbf.emoji as emo

from tgbf.plugin import TGBFPlugin
from tgbf.lamden.connect import Connect
from telegram.ext import CommandHandler, CallbackContext
from telegram import Update, ParseMode
from tgbf.web import EndpointAction


class Send(TGBFPlugin):

    def load(self):
        if not self.table_exists("send"):
            sql = self.get_resource("create_send.sql")
            self.execute_sql(sql)

        self.add_handler(CommandHandler(
            self.name,
            self.send_callback,
            run_async=True))

        web_pass = self.config.get("web_secret")
        endpoint = EndpointAction(self.send_endpoint, web_pass)
        self.add_endpoint(self.name, endpoint)

    def send_endpoint(self):
        res = self.execute_sql(self.get_resource("select_send.sql"))

        if not res["success"]:
            return {"ERROR": res["data"]}
        if not res["data"]:
            return {"ERROR": "NO DATA"}

        return res["data"]

    @TGBFPlugin.send_typing
    def send_callback(self, update: Update, context: CallbackContext):
        if len(context.args) != 2:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN_V2)
            return

        amount = context.args[0]

        try:
            # Check if amount is valid
            amount = float(amount)
        except:
            msg = f"{emo.ERROR} Amount not valid"
            update.message.reply_text(msg)
            return

        if not amount.is_integer():
            msg = f"{emo.ERROR} Amount needs to be a whole number"
            update.message.reply_text(msg)
            return

        amount = int(amount)

        # TODO: How to validate this address?
        to_address = context.args[1]

        from_wallet = self.get_wallet(update.effective_user.id)
        lamden = Connect(wallet=from_wallet)

        message = update.message.reply_text(f"{emo.HOURGLASS} Sending TAU...")

        try:
            # Send TAU
            send = lamden.post_transaction(amount, to_address)
        except Exception as e:
            msg = f"Could not send transaction: {e}"
            message.edit_text(f"{emo.ERROR} {e}")
            logging.error(msg)
            self.notify(msg)
            return

        logging.info(f"Sent {amount} TAU from {from_wallet.verifying_key} to {to_address}: {send}")

        if "error" in send:
            msg = f"Transaction replied error: {send['error']}"
            message.edit_text(f"{emo.ERROR} {send['error']}")
            logging.error(msg)
            return

        # Get transaction hash
        tx_hash = send["hash"]

        # Insert details into database
        self.execute_sql(
            self.get_resource("insert_send.sql"),
            from_wallet.verifying_key,
            to_address,
            amount,
            tx_hash)

        ex_url = lamden.cfg.get("explorer", lamden.chain)

        message.edit_text(
            f"{emo.MONEY} Sent `{amount}` TAU\n"
            f"[View Transaction on Explorer]({ex_url}/transactions/{tx_hash})",
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True)
