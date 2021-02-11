import logging
from enum import Enum

import tgbf.emoji as emo
import tgbf.utils as utl

from telegram import ParseMode, Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from telegram.utils.helpers import escape_markdown as esc_mk
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin
from tgbf.web import EndpointAction


class Confirm(Enum):
    OK = 1
    NOK = 2


class Tip(TGBFPlugin):

    def load(self):
        if not self.table_exists("tips"):
            sql = self.get_resource("create_tips.sql")
            self.execute_sql(sql)

        self.add_handler(CommandHandler(
            self.name,
            self.tip_callback,
            run_async=True))

        self.add_handler(CallbackQueryHandler(
            self.confirm_callback))

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

        try:
            # Check if amount is valid
            amount = float(amount)
        except:
            msg = f"{emo.ERROR} Amount not valid"
            update.message.reply_text(msg)
            return

        if amount.is_integer():
            amount = int(amount)

        context.user_data["update"] = update
        context.user_data["args"] = context.args

        limit = self.config.get("confirm_limit")

        if limit and float(amount) > float(limit):
            update.message.reply_text(
                f"{emo.HOURGLASS} Sending `{amount}` {esc_mk('TAU...', version=2)}",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=self.button_callback())
            return

        message = update.message.reply_text(
            f"{emo.HOURGLASS} Sending `{amount}` {esc_mk('TAU...', version=2)}",
            parse_mode=ParseMode.MARKDOWN_V2)

        context.user_data["message"] = message

        self.send_transaction(context)

    def confirm_callback(self, update: Update, context: CallbackContext):
        query = update.callback_query
        message = query.message
        data = query.data

        if "update" not in context.user_data:
            context.bot.answer_callback_query(query.id, f"{emo.STOP} Wrong user")
            return

        original_user = context.user_data["update"].effective_user.id
        current_user = update.effective_user.id

        if original_user != current_user:
            print("WRONG USER!")
            return

        if data == Confirm.NOK.name:
            message.edit_text(f"{emo.STOP} Canceled by user")
            context.bot.answer_callback_query(query.id, f"{emo.STOP} Canceled")
        else:
            context.user_data["message"] = message
            context.bot.answer_callback_query(query.id, f"{emo.DONE} Confirmed")
            self.send_transaction(context)

    def button_callback(self):
        buttons = [
            InlineKeyboardButton("Confirm", callback_data=Confirm.OK.name),
            InlineKeyboardButton("Cancel", callback_data=Confirm.NOK.name)
        ]

        menu = utl.build_menu(buttons, n_cols=2)
        return InlineKeyboardMarkup(menu, resize_keyboard=True)

    def send_transaction(self, context: CallbackContext):
        message = context.user_data["message"]
        update = context.user_data["update"]
        args = context.user_data["args"]

        reply = update.message.reply_to_message

        to_user_id = reply.from_user.id
        from_user_id = update.effective_user.id

        from_wallet = self.get_wallet(from_user_id)
        lamden = Connect(wallet=from_wallet)

        # Get address to which we want to tip
        to_address = self.get_wallet(to_user_id).verifying_key

        amount = float(args[0])

        if amount.is_integer():
            amount = int(amount)

        try:
            # Send TAU
            tip = lamden.post_transaction(amount, to_address)
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
            f"{emo.MONEY} {esc_mk(to_user, version=2)} received `{amount}` TAU\n"
            f"[View Transaction on Explorer]({ex_url}/transactions/{tx_hash})",
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True)

        try:
            # Notify user about tip
            context.bot.send_message(
                to_user_id,
                f"You received `{amount}` TAU from {esc_mk(from_user, version=2)}\n"
                f"[View Transaction on Explorer]({ex_url}/transactions/{tx_hash})",
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=True)
            logging.info(f"User {to_user_id} notified about tip of {amount} TAU")
        except Exception as e:
            logging.info(f"User {to_user_id} could not be notified about tip: {e} - {update}")

