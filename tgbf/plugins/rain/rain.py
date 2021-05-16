import html
import logging
import tgbf.emoji as emo

from telegram import Update, ParseMode
from telegram.ext import CommandHandler, CallbackContext
from datetime import datetime, timedelta
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Rain(TGBFPlugin):

    STAMPS = [29, 23, 20, 19, 18, 17]

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
        if not context.args or len(context.args) != 3:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        wallet = self.get_wallet(update.effective_user.id)
        lamden = Connect(wallet)

        token_name = context.args[0].upper()
        amount_total = context.args[1]
        time_frame = context.args[2]

        token_contract = None
        for token in lamden.tokens:
            if token_name == token[0]:
                token_contract = token[1]
                break

        if not token_contract:
            msg = f"{emo.ERROR} Token not found"
            update.message.reply_text(msg)
            return

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
            update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
            return

        t_frame = time_frame[:-1]
        t_unit = time_frame[-1:].lower()

        try:
            # Check if timeframe is valid
            t_frame = float(t_frame)
        except:
            msg = f"{emo.ERROR} Time frame not valid"
            logging.error(f"{msg} - {update}")
            update.message.reply_text(msg)
            return

        # Determine last valid date time for the airdrop
        if t_unit == "m":
            last_time = datetime.utcnow() - timedelta(minutes=t_frame)
        elif t_unit == "h":
            last_time = datetime.utcnow() - timedelta(hours=t_frame)
        else:
            msg = f"{emo.ERROR} Unsupported time unit detected!"
            logging.error(f"{msg} - {update}")
            update.message.reply_text(msg)
            self.notify(msg)
            return

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

        # Exclude own user from users to airdrop on
        user_data = [u for u in res["data"] if u[0] != update.effective_user.id]

        if len(user_data) < 1:
            msg = f"{emo.ERROR} No users found for given time frame"
            logging.error(f"{msg} - {update}")
            update.message.reply_text(msg)
            return

        msg = f"{emo.RAIN} Initiating rain clouds..."
        message = update.message.reply_text(msg)

        # Amount to airdrop to one user
        amount_single = float(f"{(amount_total / len(user_data)):.2f}")

        from_user = update.message.from_user
        from_username = "@" + from_user.username if from_user.username else from_user.first_name

        if amount_single.is_integer():
            amount_single = int(amount_single)

        # --- TEMP ---
        # TODO: Remove temporal fix
        amount_single = int(amount_single)
        if amount_single == 0:
            msg = f"{emo.ERROR} Individual amount too low"
            message.edit_text(msg)
            return
        # --- TEMP ---

        msg = f"Rained <code>{amount_single}</code> {token_name} each to following users:\n"
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
            msg += html.escape(to_username) + suffix

            logging.info(
                f"User {to_username} ({to_user_id}) will be "
                f"rained on with {amount_single} TAU to wallet {address}")

        # Remove last suffix
        msg = msg[:-len(suffix)]

        contract = self.config.get("contract")
        function = self.config.get("function")

        try:
            approved = lamden.get_approved_amount(contract, token_contract)
            approved = approved["value"] if "value" in approved else 0
            approved = approved if approved is not None else 0

            if amount_total > float(approved):
                app = lamden.approve_contract(contract, token_contract)
                mes = f"Approving {contract}: {app}"
                logging.info(mes)

            # Calculate stamp costs
            stamps_to_use = 0
            for a in range(len(addresses)):
                try:
                    stamps_to_use += self.STAMPS[a]
                except IndexError:
                    stamps_to_use += self.STAMPS[-1]

            res = lamden.post_transaction(
                stamps_to_use,
                contract,
                function,
                {"addresses": addresses, "amount": amount_single, "contract": token_contract})

            logging.info(f"Rained {amount_total} {token_name} from {from_username} on {len(user_data)} users: {res}")
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

        success, result = lamden.tx_succeeded(tx_hash)

        if not success:
            message.edit_text(f"{emo.ERROR} {result}")
            logging.error(f"Transaction not successful: {result}")
            return

        url = lamden.explorer_url
        link = f'<a href="{url}/transactions/{tx_hash}">View Transaction on Explorer</a>'

        message.edit_text(
            f"{msg}\n\n{link}",
            parse_mode=ParseMode.HTML)

        sql = self.get_resource("insert_rain.sql")

        for user in user_data:
            to_user_id = user[0]

            # Insert details into database
            self.execute_sql(sql, from_user.id, to_user_id, amount_single, tx_hash)

            try:
                # Notify user about tip
                context.bot.send_message(
                    to_user_id,
                    f"You received <code>{amount_single}</code> {token_name} from {html.escape(from_username)}\n{link}",
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True)
                logging.info(f"User {to_user_id} notified about rain of {amount_single} {token_name}")
            except Exception as e:
                logging.info(f"User {to_user_id} could not be notified about rain: {e} - {update}")
