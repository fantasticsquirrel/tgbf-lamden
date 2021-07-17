import os
import time
import logging
import tgbf.emoji as emo
import tgbf.utils as utl

from threading import Thread
from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin
from tgbf.lamden.rocketswap import Rocketswap


class Buy(TGBFPlugin):

    RS_CONTRACT = "con_rocketswap_official_v1_1"

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.buy_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def buy_callback(self, update: Update, context: CallbackContext):
        if len(context.args) == 2:
            check_msg = f"{emo.HOURGLASS} Checking subscription..."
            message = update.message.reply_text(check_msg)

            usr_id = update.effective_user.id
            wallet = self.get_wallet(usr_id)
            lamden = Connect(wallet)

            deposit = lamden.get_contract_variable(
                self.config.get("contract"),
                "data",
                wallet.verifying_key
            )

            deposit = deposit["value"] if "value" in deposit else 0
            deposit = float(str(deposit)) if deposit else float("0")

            if deposit == 0:
                update.message.reply_text(
                    f"You are currently not subscribed. Please use /goldape "
                    f"to subscribe to new token listing and token trading.")
                return
        else:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        tau_amount = context.args[0]

        try:
            tau_amount = float(tau_amount)
        except:
            msg = f"{emo.ERROR} First argument needs to be a valid amount"
            update.message.reply_text(msg)
            return

        # ----------------------

        # TODO: Temporal fix
        if tau_amount.is_integer():
            tau_amount = int(tau_amount)
        else:
            msg = f"{emo.ERROR} Amount currently needs to be an Integer"
            update.message.reply_text(msg)
            return

        # ----------------------

        token = context.args[1].upper()
        token_contract = str()

        found = False
        for tkn in self.execute_sql(self.get_resource("select_token.sql"))["data"]:
            if tkn.upper().upper() == token:
                found = True

        if not found:
            msg = f"{emo.ERROR} Invalid token symbol"
            update.message.reply_text(msg)
            return

        check_msg = f"{emo.HOURGLASS} Buying {token}..."
        message.edit_text(check_msg)

        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet)

        try:
            # Check if Rocketswap contract is approved to spend TAU
            approved = lamden.get_approved_amount(self.RS_CONTRACT)
            approved = approved["value"] if "value" in approved else 0
            approved = approved if approved is not None else 0

            msg = f"Approved amount of TAU for {self.RS_CONTRACT}: {approved}"
            logging.info(msg)

            if tau_amount > float(approved):
                app = lamden.approve_contract(self.RS_CONTRACT)
                msg = f"Approved {self.RS_CONTRACT} for TAU: {app}"
                logging.info(msg)
        except Exception as e:
            logging.error(f"Error approving {self.RS_CONTRACT} for TAU: {e}")
            message.edit_text(f"{emo.ERROR} {e}")
            return

        if not tau_amount or tau_amount <= 0:
            msg = f"{emo.ERROR} Tokens couldn't be sold"
            message.edit_text(msg)
            return

        token_price = lamden.get_contract_variable("con_rocketswap_official_v1_1", "prices", self.GOLD_CONTRACT)
        token_price = float(token_price["value"])

        gold_amount_to_buy = tau_amount / token_price
        min_gold = gold_amount_to_buy / 100 * (100 - self.config.get("slippage"))

        # TODO: Remove. Temporal fix
        min_gold = int(min_gold)

        kwargs = {
            "contract": self.GOLD_CONTRACT,
            "currency_amount": total_tau,
            "minimum_received": min_gold,
            "token_fees": False
        }

        try:
            # Call contract to BUY GOLD
            buy = lamden.post_transaction(
                stamps=150,
                contract=self.RS_CONTRACT,
                function="buy",
                kwargs=kwargs
            )
        except Exception as e:
            logging.error(f"Error calling Rocketswap contract: {e}")
            message.edit_text(f"{emo.ERROR} {e}")
            return

        logging.info(f"Executed Rocketswap - buy contract: {buy}")

        if "error" in buy:
            logging.error(f"Rocketswap - buy contract returned error: {buy['error']}")
            message.edit_text(f"{emo.ERROR} {buy['error']}")
            return

        # Get transaction hash
        tx_hash = buy["hash"]
        logging.info(f"Buying gold tx hash {tx_hash}")

        # Wait for transaction to be completed
        success, result = lamden.tx_succeeded(tx_hash)

        if not success:
            logging.error(f"Transaction not successful: {result}")
            msg = f"{emo.ERROR} Buying GOLD not successful: {result}"
            message.edit_text(msg)
            return

        msg = f"{emo.DONE} Tokens converted to GOLD"
        message.edit_text(msg)

    def button_callback(self, update: Update, context: CallbackContext):
        data = update.callback_query.data

        if not data.startswith(self.name):
            return

        if "sell_list" not in context.user_data:
            msg = f"{emo.WARNING} Message expired"
            context.bot.answer_callback_query(update.callback_query.id, msg)
            return

        sell_list = context.user_data["sell_list"]

        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet)

        message = update.callback_query.message
        message.edit_text(f"{emo.HOURGLASS} Selling assets...")

        threads = [None] * len(sell_list)
        results = [None] * len(sell_list)

        for i in range(len(sell_list)):
            threads[i] = Thread(target=self.sell_asset, args=(lamden, sell_list[i], results, i))
            threads[i].start()
            threads[i].join()

            # Make sure that transactions are processed in order
            time.sleep(0.1)

        message.edit_text(f"{emo.HOURGLASS} Converting to GOLD...")

        total_tau = 0
        for res in results:
            if res:
                try:
                    res = float(res)
                except:
                    res = 0
            else:
                res = 0
            total_tau += res

