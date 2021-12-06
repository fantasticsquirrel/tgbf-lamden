import html
import logging
import tgbf.emoji as emo

from telegram import ParseMode, Update
from telegram.ext import CommandHandler, CallbackContext
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Tip(TGBFPlugin):

    def load(self):
        if not self.table_exists("tips"):
            sql = self.get_resource("create_tips.sql")
            self.execute_sql(sql)

        self.add_handler(CommandHandler(
            self.name,
            self.tip_callback,
            run_async=True))

    @TGBFPlugin.public
    @TGBFPlugin.send_typing
    def tip_callback(self, update: Update, context: CallbackContext):
        if len(context.args) < 2:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        reply = update.message.reply_to_message

        if not reply:
            msg = f"{emo.ERROR} Tip a user by replying to his message"
            logging.info(f"{msg} - {update}")
            update.message.reply_text(msg)
            return

        token_name = context.args[0].upper()
        amount = context.args[1]

        to_user_id = reply.from_user.id
        from_user_id = update.effective_user.id

        from_wallet = self.get_wallet(from_user_id)
        lamden = Connect(wallet=from_wallet)

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

        usr_msg = str()
        if len(context.args) > 2:
            usr_msg = f"Message: {' '.join(context.args[2:])}"

        try:
            # Check if amount is valid
            amount = float(amount)
        except:
            msg = f"{emo.ERROR} Amount not valid"
            update.message.reply_text(msg)
            return

        # Check if amount is negative
        if amount < 0:
            msg = f"{emo.ERROR} Amount not valid"
            update.message.reply_text(msg)
            return

        if amount.is_integer():
            amount = int(amount)

        # Get address to which we want to tip
        to_address = self.get_wallet(to_user_id).verifying_key

        message = update.message.reply_text(f"{emo.HOURGLASS} Sending {token_name}...")

        try:
            # Send token
            tip = lamden.send(amount, to_address, token=token_contract)
        except Exception as e:
            msg = f"Could not send transaction: {e}"
            message.edit_text(f"{emo.ERROR} {e}")
            logging.error(msg)
            self.notify(msg)
            return

        if "error" in tip:
            msg = f"Transaction replied error: {tip['error']}"
            message.edit_text(f"{emo.ERROR} {tip['error']}")
            logging.error(msg)
            return

        # Get transaction hash
        tx_hash = tip["hash"]

        logging.info(f"Tipped {amount} {token_name} from {from_user_id} to {to_user_id}: {tip}")

        link = f'<a href="{lamden.explorer_url}/transactions/{tx_hash}">View Transaction on Explorer</a>'

        to_user = reply.from_user.first_name

        if update.effective_user.username:
            from_user = f"@{update.effective_user.username}"
        else:
            from_user = update.effective_user.first_name

        message.edit_text(
            f"{emo.MONEY} {html.escape(to_user)} received <code>{amount}</code> {token_name}\n{link}",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True)

        # Wait for transaction to be completed
        success, result = lamden.tx_succeeded(tx_hash)

        if not success:
            logging.error(f"Transaction not successful: {result}")

            link = f'<a href="{lamden.explorer_url}/transactions/{tx_hash}">TRANSACTION FAILED</a>'

            message.edit_text(
                f"{emo.STOP} {to_user} <del>received</del> <code>{amount}</code> {token_name}\n{link}",
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True)
            return

        """
        # Insert details into database
        self.execute_sql(
            self.get_resource("insert_tip.sql"),
            from_user_id,
            to_user_id,
            amount,
            tx_hash)
        """

        try:
            # Notify user about tip
            context.bot.send_message(
                to_user_id,
                f"You received <code>{amount}</code> {token_name} from {from_user}\n{link}\n\n{usr_msg}",
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True)
            logging.info(f"User {to_user_id} notified about tip of {amount} {token_name}")
        except Exception as e:
            logging.info(f"User {to_user_id} could not be notified about tip: {e} - {update}")
