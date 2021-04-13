import json
import logging
import requests
import tgbf.emoji as emo
import tgbf.utils as utl

from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Otc(TGBFPlugin):

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.otc_callback,
            run_async=True))

        self.add_handler(CallbackQueryHandler(
            self.execute_trade_callback,
            run_async=True))

    @TGBFPlugin.private
    @TGBFPlugin.send_typing
    def otc_callback(self, update: Update, context: CallbackContext):
        context.user_data.clear()

        # If no arguments, show how to use
        if not context.args:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        contract = self.config.get("contract")
        function = self.config.get("function")

        # Taking an offer
        if len(context.args) == 1:
            otc_id = context.args[0]

            wallet = self.get_wallet(update.effective_user.id)
            lamden = Connect(wallet)

            url = f"{lamden.node_url}/contracts/{contract}/data"

            try:
                res = requests.get(url, params={"key": otc_id})
            except Exception as e:
                logging.error(f"Error retrieving OTC {otc_id}: {e}")
                update.message.reply_text(f"{emo.ERROR} {e}")
                return

            otc = json.loads(res.text)["value"]

            if not otc:
                msg = f"{emo.ERROR} No entry found"
                update.message.reply_text(msg)
                return

            logging.info(f"{otc_id} {otc}")

            offer_amount = float(otc['offer_amount']['__fixed__'])
            offer_amount = int(offer_amount) if offer_amount.is_integer() else offer_amount

            take_amount = float(otc['take_amount']['__fixed__'])
            take_amount = int(take_amount) if take_amount.is_integer() else take_amount

            msg = f"BUY {offer_amount} {otc['offer_token']}\n" \
                  f"FOR {take_amount} {otc['take_token']}"

            # If not available anymore then only show details
            if otc["state"] == "CANCELED":
                ex = f"{emo.INFO} Trade was canceled"
                update.message.reply_text(
                    f"<code>{msg}\n\n{ex}</code>",
                    parse_mode=ParseMode.HTML)
                return
            if otc["state"] == "EXECUTED":
                ex = f"{emo.INFO} Trade was executed"
                update.message.reply_text(
                    f"<code>{msg}\n\n{ex}</code>",
                    parse_mode=ParseMode.HTML)
                return

            fee = float(otc['fee']['__fixed__'])
            fee = int(fee) if fee.is_integer() else fee
            fee = f"Excluding {fee}% Maker and Taker fee"

            context.user_data["otc"] = otc
            context.user_data["otc_id"] = otc_id
            context.user_data["lamden"] = lamden
            context.user_data["contract"] = contract
            context.user_data["function"] = function
            context.user_data["confirmed"] = False

            update.message.reply_text(
                f"<code>{msg}\n{fee}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=self.take_offer_button_callback())

    def execute_trade_callback(self, update: Update, context: CallbackContext):
        if update.callback_query.data != self.name:
            return

        message = update.callback_query.message

        # User didn't confirm yet with second button click
        if not context.user_data["confirmed"]:
            context.user_data["confirmed"] = True

            message.edit_text(
                f"<code>{message.text}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=self.confirm_offer_button_callback())

        # User already confirmed
        else:
            message.edit_text(
                f"<code>{message.text}</code>\n\n{emo.HOURGLASS} Executing trade ...",
                parse_mode=ParseMode.HTML)

            otc = context.user_data["otc"]
            otc_id = context.user_data["otc_id"]
            lamden = context.user_data["lamden"]
            contract = context.user_data["contract"]
            function = context.user_data["function"]

            try:
                # Check if contract is approved to spend TAU
                approved = lamden.get_approved_amount(
                    contract=contract,
                    token=otc["take_token"])

                approved = approved["value"] if "value" in approved else 0
                approved = approved if approved is not None else 0

                logging.info(f"Approved amount of TAU for {contract}: {approved}")

                # Approving exact amount
                if float(otc["take_amount"]['__fixed__']) > float(approved):
                    app = lamden.approve_contract(
                        contract=contract,
                        token=otc["take_token"],
                        amount=otc["take_amount"]['__fixed__'])

                    logging.info(f"Approved {contract}: {app}")
            except Exception as e:
                logging.error(f"Error approving contract {contract}: {e}")
                message.edit_text(
                    f"<code>{message.text}</code>\n\n{emo.ERROR} {e}",
                    parse_mode=ParseMode.HTML)
                return

            try:
                # Call OTC contract
                ret = lamden.post_transaction(
                    stamps=80,
                    contract=contract,
                    function=function,
                    kwargs={"offer_id": otc_id})
            except Exception as e:
                logging.error(f"Error calling OTC contract: {e}")
                message.edit_text(
                    f"<code>{message.text}</code>\n\n{emo.ERROR} {e}",
                    parse_mode=ParseMode.HTML)
                return

            logging.info(f"Executed OTC contract: {ret}")

            if "error" in ret:
                logging.error(f"OTC contract returned error: {ret['error']}")
                message.edit_text(
                    f"<code>{message.text}</code>\n\n{emo.ERROR} {ret['error']}",
                    parse_mode=ParseMode.HTML)
                return

            # Get transaction hash
            tx_hash = ret["hash"]

            # Wait for transaction to be completed
            success, result = lamden.tx_succeeded(tx_hash)

            if not success:
                logging.error(f"OTC transaction not successful: {result}")
                message.edit_text(
                    f"<code>{message.text}</code>\n\n{emo.ERROR} {result}",
                    parse_mode=ParseMode.HTML)
                return

            trade_url = f"{lamden.explorer_url}/transactions/{tx_hash}"
            trade_msg = f'{emo.DONE} <a href="{trade_url}">Trade executed</a>'

            message.edit_text(
                f"<code>{message.text}</code>\n\n{trade_msg}",
                parse_mode=ParseMode.HTML)

            msg = f"{emo.DONE} Trade executed"
            context.bot.answer_callback_query(update.callback_query.id, msg)

    def take_offer_button_callback(self):
        menu = utl.build_menu([InlineKeyboardButton("Take offer", callback_data=self.name)])
        return InlineKeyboardMarkup(menu, resize_keyboard=True)

    def confirm_offer_button_callback(self):
        menu = utl.build_menu([InlineKeyboardButton("CONFIRM TO EXECUTE TRADE", callback_data=self.name)])
        return InlineKeyboardMarkup(menu, resize_keyboard=True)
