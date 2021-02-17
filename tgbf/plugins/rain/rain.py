import logging
import tgbf.emoji as emo

from telegram import Update, ParseMode
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
                parse_mode=ParseMode.MARKDOWN_V2)
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

        # Check if timeframe is valid and includes time unit
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

        # Number of users that will receive the airdrop
        user_count = len(user_data)

        # Amount of TAU to airdrop to one user
        amount_single = float(f"{(amount_total / user_count):.2f}")

        from_user = update.message.from_user
        from_username = "@" + from_user.username if from_user.username else from_user.first_name

        msg = f"{emo.RAIN} Initiating rain clouds..."
        message = update.message.reply_text(msg)

        msg = f"Rained {amount_single} TAU each to following users:\n"
        suffix = ", "

        for user in user_data:
            to_user_id = user[0]
            to_username = user[1]

            # TODO: Is that needed? We already exclude initiator from
            if from_username == to_username:
                continue

            msg += to_username + suffix

        wallet = self.get_wallet(update.effective_user.id)
        api = Connect(wallet)

        try:
            # TODO: Check if tx was successful
            res = api.post_transaction(500, "con_multi_send5", "send", kwargs)
        except Exception as e:
            msg = f"Could not execute smart contract: {e}"
            message.edit_text(f"{emo.ERROR} {e}")
            logging.error(msg)
            self.notify(msg)
            return

        # Insert details into database
        sql = self.get_resource("insert_rain.sql")
        self.execute_sql(sql, from_user.id, to_user_id, T2X.to_atom(amount_single), txid)

        msg = msg[:-len(suffix)]
        message.edit_text(msg)



        """
        client = ContractingClient()
        con_multi_send = client.get_contract("con_multi_send5")

        addresses = [
                "a8267cf0ba6aaa62596133276a610731a2bea37a43cf5b15a6bc3f6b67b3975d",
                "2a61771c19cd8bd01c629d91c9a45d547249eec5dd80905bc8e929706dd47fdb"
            ]

        con_multi_send.send(addresses=addresses, amount=float(10))
        """

        approved = api.get_approved_amount("con_multi_send5")
        approved = approved["value"] if "value" in approved else 0
        approved = approved if approved is not None else 0

        if amount_single > approved:
            api.approve_amount("con_multi_send5")

        kwargs = {
            "addresses": [
                "a8267cf0ba6aaa62596133276a610731a2bea37a43cf5b15a6bc3f6b67b3975d",
                "2a61771c19cd8bd01c629d91c9a45d547249eec5dd80905bc8e929706dd47fdb"
            ],
            "amount": float(10)
        }
