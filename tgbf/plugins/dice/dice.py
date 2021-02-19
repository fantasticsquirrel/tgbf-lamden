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

        try:
            number = int(number)
            if number < 1 or number > 6:
                raise ValueError()
        except:
            # Validate number of points to bet on
            msg = f"{emo.ERROR} Number of points not valid. " \
                  f"Provide a whole number between 1 and 6 (second argument)"
            update.message.reply_text(msg)
            return

        wallet = self.get_wallet(update.effective_user.id)
        lamden = Connect(wallet)

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
                update.message.reply_text(f"{emo.ERROR} {result}")
                return

        # TODO: Show link to transaction
        update.message.reply_text(f"Result: {result}")
