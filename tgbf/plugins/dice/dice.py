import logging
import tgbf.emoji as emo

from telegram import Update, ParseMode
from telegram.ext import CommandHandler, CallbackContext
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

    @TGBFPlugin.whitelist
    @TGBFPlugin.send_typing
    def dice_callback(self, update: Update, context: CallbackContext):
        if len(context.args) != 2:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        amount = context.args[0]
        number = context.args[1]

        min_amount = self.config.get("min_amount")
        max_amount = self.config.get("max_amount")

        try:
            amount = float(amount)
            if amount < min_amount or amount > max_amount:
                raise ValueError()
        except:
            # Validate amount of TAU to bet
            msg = f"{emo.ERROR} Amount not valid. " \
                  f"Provide a value between {min_amount} and {max_amount} TAU (first argument)"
            update.message.reply_text(msg)
            return

        # Convert to Integer if possible
        if amount.is_integer():
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

        bet_msg = f"You bet `{amount}` TAU to roll a `{number}`"
        message = update.message.reply_text(bet_msg, parse_mode=ParseMode.MARKDOWN_V2)

        logging.info(f"{bet_msg} - {update}")

        user_id = update.effective_user.id

        wallet = self.get_wallet(user_id)
        lamden = Connect(wallet)

        try:
            # Send the bet amount to bot wallet
            send = lamden.send(amount, self.bot_wallet.verifying_key)
        except Exception as e:
            msg = f"Could not send transaction: {e}"
            message.edit_text(f"{bet_msg}/n/n{emo.ERROR} {e}")
            logging.error(msg)
            self.notify(msg)
            return

        logging.info(f"Sent {amount} TAU to bot wallet: {send}")

        if "error" in send:
            msg = f"Transaction replied error: {send['error']}"
            message.edit_text(f"{bet_msg}/n/n{emo.ERROR} {send['error']}")
            logging.error(msg)
            return

        # Get transaction hash
        tx_hash = send["hash"]

        # Insert details into database
        self.execute_sql(
            self.get_resource("insert_bet.sql"),
            user_id,
            amount,
            number,
            tx_hash)

        success, result = lamden.tx_succeeded(tx_hash)

        if not success:
            message.edit_text(f"{bet_msg}/n/n{emo.ERROR} {result}")
            logging.error(f"Transaction not successful: {result}")
            return

        url = lamden.explorer_url
        link = f"[Amount sent]({url}/transactions/{tx_hash})"

        bet_msg = f"{bet_msg}\n\n{link}"
        message.edit_text(bet_msg, parse_mode=ParseMode.MARKDOWN_V2)

        contract = self.config.get("contract")
        function = self.config.get("function")

        roll = lamden.post_transaction(500, contract, function, {})
        logging.info(f"Dice rolled: {roll}")

        # TODO: Rework
        success, result = lamden.tx_succeeded(roll["hash"])

        if not success:
            try:
                int(result)
            except:
                bet_msg = f"{bet_msg}/n/n{emo.ERROR} {result}"
                update.message.reply_text(bet_msg, parse_mode=ParseMode.MARKDOWN_V2)
                return

        # User WON!
        if int(result) == int(number):
            bet_msg = f"{bet_msg}\n\nYou rolled a {result} and WON!! {emo.MONEY}"
        # User LOST!
        else:
            bet_msg = f"{bet_msg}\n\nYou rolled a {result}\nMore luck next time! {emo.MONEY}"

        message.edit_text(bet_msg, parse_mode=ParseMode.MARKDOWN_V2)
