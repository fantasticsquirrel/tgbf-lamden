import logging
import tgbf.emoji as emo

from telegram import Update, ParseMode
from telegram.utils.helpers import escape_markdown as esc_mk
from telegram.ext import CommandHandler, CallbackContext
from datetime import datetime, timedelta
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Rain(TGBFPlugin):

    def load(self):
        if not self.table_exists("rain"):
            sql = self.get_resource("create_rain.sql")
            self.execute_sql(sql)

        self.add_handler(CommandHandler(
            self.name,
            self.rain_callback,
            run_async=True))

    @TGBFPlugin.public
    @TGBFPlugin.send_typing
    def rain_callback(self, update: Update, context: CallbackContext):
        if not context.args or len(context.args) > 2:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        # Read arguments 'amount' and 'time frame'
        if len(context.args) == 1:
            amount_total = context.args[0]
            time_frame = "3h"
        else:
            amount_total = context.args[0]
            time_frame = context.args[1]

        try:
            # Check if amount is valid
            amount_total = float(amount_total)
        except:
            msg = f"{emo.ERROR} Amount not valid"
            update.message.reply_text(msg)
            return

        # Check if time unit is included and valid
        if not time_frame.lower().endswith(("m", "h")):
            msg = f"{emo.ERROR} Allowed time units are `m` (minute) and `h` (hour)"
            update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)
            return

        time_frame = time_frame[:-1]
        time_unit = time_frame[-1:].lower()

        try:
            # Check if timeframe is valid
            time_frame = float(time_frame)
        except:
            msg = f"{emo.ERROR} Time frame not valid"
            logging.error(f"{msg} - {update}")
            update.message.reply_text(msg)
            return

        # Determine last valid date time for the airdrop
        if time_unit == "m":
            last_time = datetime.utcnow() - timedelta(minutes=time_frame)
        else:
            last_time = datetime.utcnow() - timedelta(hours=time_frame)

        chat_id = update.effective_chat.id

        # Get all users that messaged until 'last_time'
        sql = self.get_resource("select_active.sql", plugin="active")
        res = self.execute_sql(sql, chat_id, last_time, plugin="active")

        if not res["success"] or not res["data"]:
            msg = f"{emo.ERROR} Could not determine last active users"
            logging.error(f"{msg} - {update}")
            update.message.reply_text(msg)
            self.notify(msg)
            return

        # Users to airdrop to without own user
        user_data = [u for u in res["data"] if u[0] != update.effective_user.id]

        if len(user_data) < 1:
            msg = f"{emo.ERROR} No users found for given time frame"
            logging.error(f"{msg} - {update}")
            update.message.reply_text(msg)
            return

        msg = f"{emo.RAIN} Initiating rain clouds..."
        message = update.message.reply_text(msg)

        # Amount of TAU to airdrop to one user
        amount_single = float(f"{(amount_total / len(user_data)):.2f}")

        from_user = update.message.from_user
        from_username = "@" + from_user.username if from_user.username else from_user.first_name

        if amount_single.is_integer():
            amount_single = int(amount_single)

        msg = f"Rained `{amount_single}` TAU each to following users:\n"
        suffix = ", "

        # List of addresses that will get the airdrop
        addresses = list()

        for user in user_data:
            to_user_id = user[0]
            to_username = user[1]

            address = self.get_wallet(to_user_id).verifying_key

            # Add address to list of addresses to rain on
            addresses.append(address)
            # Add username to output message
            msg += esc_mk(to_username + suffix, version=2)

            logging.info(
                f"User {to_username} ({to_user_id}) will be "
                f"rained on with {amount_single} TAU to wallet {address}")

        # Remove last suffix
        msg = msg[:-len(suffix)]

        wallet = self.get_wallet(update.effective_user.id)
        lamden = Connect(wallet)

        contract = self.config.get("contract")
        function = self.config.get("function")

        try:
            approved = lamden.get_approved_amount(contract)
            approved = approved["value"] if "value" in approved else 0
            approved = approved if approved is not None else 0

            if amount_single > float(approved):
                lamden.approve_contract(contract)

            res = lamden.post_transaction(
                500,
                contract,
                function,
                {"addresses": addresses, "amount": amount_single})

            logging.info(f"Rained {amount_total} TAU from {from_username} on {len(user_data)} users: {res}")
        except Exception as e:
            msg = f"Error on posting transaction: {e}"
            message.edit_text(f"{emo.ERROR} {e}")
            logging.error(msg)
            self.notify(msg)
            return

        if "error" in res:
            msg = f"Transaction replied error: {res['error']}"
            message.edit_text(f"{emo.ERROR} {res['error']}")
            logging.error(msg)
            return

        # Get transaction hash
        tx_hash = res["hash"]

        success, result = lamden.tx_successful(tx_hash)

        if not success:
            message.edit_text(f"{emo.ERROR} {result}")
            return

        url = lamden.cfg.get("explorer", lamden.chain)
        link = f"[View Transaction on Explorer]({url}/transactions/{tx_hash})"

        msg = f"{msg}\n\n{link}"
        message.edit_text(msg, parse_mode=ParseMode.MARKDOWN_V2)

        sql = self.get_resource("insert_rain.sql")

        for user in user_data:
            to_user_id = user[0]

            # Insert details into database
            self.execute_sql(sql, from_user.id, to_user_id, amount_single, tx_hash)
