import logging
import tgbf.emoji as emo

from telegram import Update, ParseMode
from telegram.ext import CommandHandler, CallbackContext
from telegram.utils.helpers import escape_markdown as esc_mk
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Dice(TGBFPlugin):

    def load(self):
        if not self.table_exists("bets"):
            sql = self.get_resource("create_bets.sql")
            self.execute_sql(sql)

        self.add_handler(CommandHandler(
            self.name,
            self.dice_callback,
            run_async=True))

    @TGBFPlugin.blacklist
    @TGBFPlugin.send_typing
    def dice_callback(self, update: Update, context: CallbackContext):
        if len(context.args) != 2:
            min = self.config.get("min_amount")
            max = self.config.get("max_amount")

            update.message.reply_text(
                self.get_usage({"{{min}}": min, "{{max}}": max}),
                parse_mode=ParseMode.MARKDOWN)
            return

        amount = context.args[0]
        number = context.args[1]

        try:
            amount = float(amount)
        except:
            # Validate amount of TAU to bet
            msg = f"{emo.ERROR} Amount (first argument) not valid"
            update.message.reply_text(msg)
            return

        # Check that amount is an Integer
        if not amount.is_integer():
            msg = f"{emo.ERROR} Amount (first argument) needs to be a whole number"
            update.message.reply_text(msg)
            return

        amount = int(amount)

        try:
            # Validate dice number
            number = int(number)
            if number < 1 or number > 6:
                raise ValueError()
        except:
            # Validate number of points to bet on
            msg = f"{emo.ERROR} Number of points not valid. " \
                  f"Provide a whole number between 1 and 6 (as second argument)"
            update.message.reply_text(msg)
            return

        contract = self.config.get("contract")
        function = self.config.get("function")

        bet_msg = esc_mk(f"You bet {amount} TAU to roll a {number}", version=2)
        con_msg = f"{emo.HOURGLASS} Calling contract"

        logging.info(f"{bet_msg} - {update}")

        message = update.message.reply_text(
            f"{bet_msg}\n{con_msg}",
            parse_mode=ParseMode.MARKDOWN_V2)

        user_id = update.effective_user.id
        user_wallet = self.get_wallet(user_id)
        user_api = Connect(user_wallet)

        try:
            # Check if dice contract is approved to spend TAU
            approved = user_api.get_approved_amount(contract)
            approved = approved["value"] if "value" in approved else 0
            approved = approved if approved is not None else 0

            msg = f"Approved amount of TAU for {contract}: {approved}"
            logging.info(msg)

            if amount > float(approved):
                app = user_api.approve_contract(contract)
                msg = f"Approved {contract}: {app}"
                logging.info(msg)
        except Exception as e:
            logging.error(f"Error approving dice contract: {e}")
            msg = f"{bet_msg}\n{emo.ERROR} {esc_mk(str(e), version=2)}"
            message.edit_text(msg, parse_mode=ParseMode.MARKDOWN_V2)
            return

        try:
            # Call dice contract
            dice = user_api.post_transaction(
                stamps=50,
                contract=contract,
                function=function,
                kwargs={"guess": number, "amount": amount})
        except Exception as e:
            logging.error(f"Error calling dice contract: {e}")
            msg = f"{bet_msg}\n{emo.ERROR} {esc_mk(str(e), version=2)}"
            message.edit_text(msg, parse_mode=ParseMode.MARKDOWN_V2)
            return

        logging.info(f"Executed dice contract: {dice}")

        if "error" in dice:
            logging.error(f"Dice contract returned error: {dice['error']}")
            msg = f"{bet_msg}\n{emo.ERROR} {esc_mk(dice['error'], version=2)}"
            message.edit_text(msg, parse_mode=ParseMode.MARKDOWN_V2)
            return

        # Get transaction hash
        tx_hash = dice["hash"]

        # Wait for transaction to be completed
        success, result = user_api.tx_succeeded(tx_hash)

        if not success:
            logging.error(f"Transaction not successful: {result}")
            msg = f"{bet_msg}\n{emo.ERROR} {esc_mk(result, version=2)}"
            message.edit_text(msg, parse_mode=ParseMode.MARKDOWN_V2)
            return

        ex_url = f"{user_api.explorer_url}/transactions/{tx_hash}"
        con_msg = f"{emo.DONE} [Contract executed]({ex_url})"

        if int(result["result"]) == int(number):
            amount_back = amount * 5
            res_msg = f"YOU WON {amount_back} TAU!! {emo.MONEY_FACE}"

            logging.info(f"User WON {amount_back} TAU")
        else:
            amount_back = 0
            res_msg = f"You rolled a {result['result']} and lost {emo.SAD}"

            logging.info(f"User LOST")

        message.edit_text(
            f"{bet_msg}\n{con_msg}\n\n{esc_mk(res_msg, version=2)}",
            parse_mode=ParseMode.MARKDOWN_V2)

        # Insert details into database
        self.execute_sql(
            self.get_resource("insert_bet.sql"),
            user_id,
            amount,
            number,
            tx_hash,
            result["result"],
            amount_back,
            "-")
