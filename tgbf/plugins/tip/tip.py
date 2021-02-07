import logging
import tgbf.emoji as emo

from telegram import ParseMode, Update
from lamden.crypto.wallet import Wallet
from telegram.ext import CommandHandler, CallbackContext
from telegram.utils.helpers import escape_markdown as esc_mk
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin
from tgbf.web import EndpointAction


class Tip(TGBFPlugin):

    def load(self):
        if not self.table_exists("tips"):
            sql = self.get_resource("create_tips.sql")
            self.execute_sql(sql)

        self.add_handler(CommandHandler(
            self.name,
            self.tip_callback,
            run_async=True),
            group=1)

        web_pass = self.config.get("web_secret")
        endpoint = EndpointAction(self.tip_endpoint, web_pass)
        self.add_endpoint(self.name, endpoint)

    def tip_endpoint(self):
        res = self.execute_sql(self.get_resource("select_tips.sql"))

        if not res["success"]:
            return {"ERROR": res["data"]}
        if not res["data"]:
            return {"ERROR": "NO DATA"}

        return res["data"]

    @TGBFPlugin.public
    @TGBFPlugin.send_typing
    def tip_callback(self, update: Update, context: CallbackContext):
        if len(context.args) != 1:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN_V2)
            return

        reply = update.message.reply_to_message

        if not reply:
            msg = f"{emo.ERROR} Tip a user by replying to his message"
            logging.error(f"{msg} - {update}")
            update.message.reply_text(msg)
            return

        amount = context.args[0]
        to_user_id = reply.from_user.id
        from_user_id = update.effective_user.id

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

        # Get wallet from which we want to tip
        sql = self.get_resource("select_wallet.sql", plugin="wallets")
        res = self.execute_sql(sql, from_user_id, plugin="wallets")

        if not res["data"]:
            msg = f"{emo.ERROR} Can't retrieve your wallet"
            update.message.reply_text(f"{msg} - {update}")
            self.notify(msg)
            return

        from_wallet = Wallet(res["data"][0][2])
        lamden = Connect(wallet=from_wallet)

        # Get wallet to which we want to tip
        res = self.execute_sql(sql, to_user_id, plugin="wallets")

        if res["data"]:
            to_address = res["data"][0][1]
        else:
            to_wallet = Wallet()

            # Save wallet to database
            self.execute_sql(
                self.get_resource("insert_wallet.sql", plugin="wallets"),
                to_user_id,
                to_wallet.verifying_key,
                to_wallet.signing_key,
                plugin="wallets")

            to_address = to_wallet.verifying_key

        message = update.message.reply_text(f"{emo.HOURGLASS} Sending TAU...")

        try:
            # Send TAU
            tip = lamden.post_transaction(from_wallet, amount, to_address)
        except Exception as e:
            msg = f"Could not send transaction: {e}"
            message.edit_text(f"{emo.ERROR} {e}")
            logging.error(msg)
            self.notify(msg)
            return

        logging.info(f"Tipped {amount} TAU from {from_user_id} to {to_user_id}: {tip}")

        if "error" in tip:
            msg = f"Transaction replied error: {tip['error']}"
            message.edit_text(f"{emo.ERROR} {tip['error']}")
            logging.error(msg)
            return

        # Get transaction hash
        tx_hash = tip["hash"]

        # Insert details into database
        self.execute_sql(
            self.get_resource("insert_tip.sql"),
            from_user_id,
            to_user_id,
            amount,
            tx_hash)

        to_user = reply.from_user.first_name

        if update.effective_user.username:
            from_user = f"@{update.effective_user.username}"
        else:
            from_user = update.effective_user.first_name

        ex_url = lamden.cfg.get("explorer", lamden.chain)

        message.edit_text(
            f"{emo.MONEY} {esc_mk(to_user)} received `{amount}` TAU\n"
            f"[View Transaction on Explorer]({ex_url}/transactions/{tx_hash})",
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True)

        try:
            # Notify user about tip
            context.bot.send_message(
                to_user_id,
                f"You received `{amount}` TAU from {esc_mk(from_user)}\n"
                f"[View Transaction on Explorer]({ex_url}/transactions/{tx_hash})",
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=True)
            logging.info(f"User {to_user_id} notified about tip of {amount} TAU")
        except Exception as e:
            logging.info(f"User {to_user_id} could not be notified about tip: {e} - {update}")
