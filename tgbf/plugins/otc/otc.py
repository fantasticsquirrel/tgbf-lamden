import json
import logging
import requests
import tgbf.emoji as emo
import tgbf.utils as utl

from enum import auto
from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, \
    KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler, ConversationHandler, \
    MessageHandler, Filters
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Otc(TGBFPlugin):

    # Workflow Stages
    OFFER_TOKEN = auto()
    OFFER_AMOUNT = auto()
    TAKE_TOKEN = auto()
    TAKE_AMOUNT = auto()
    SUMMARY = auto()

    # Buttons
    CANCEL = "Cancel"
    CONFIRM = "Confirm"

    def load(self):

        self.add_handler(ConversationHandler(
            entry_points=[CommandHandler(self.name, self.start)],
            states={
                self.OFFER_TOKEN: [
                    MessageHandler(Filters.regex(f"^({self.CANCEL})$"), self.cancel),
                    MessageHandler(Filters.text, self.offer_token, pass_user_data=True)
                ],
                self.OFFER_AMOUNT: [
                    MessageHandler(Filters.regex(f"^({self.CANCEL})$"), self.cancel),
                    MessageHandler(Filters.text, self.offer_amount, pass_user_data=True)
                ],
                self.TAKE_TOKEN: [
                    MessageHandler(Filters.regex(f"^({self.CANCEL})$"), self.cancel),
                    MessageHandler(Filters.text, self.take_token, pass_user_data=True)
                ],
                self.TAKE_AMOUNT: [
                    MessageHandler(Filters.regex(f"^({self.CANCEL})$"), self.cancel),
                    MessageHandler(Filters.text, self.take_amount, pass_user_data=True)
                ],
                self.SUMMARY: [
                    MessageHandler(Filters.regex(f"^({self.CANCEL})$"), self.cancel),
                    MessageHandler(Filters.regex(f"^({self.CONFIRM})$"), self.summary, pass_user_data=True),
                ]
            },
            fallbacks=[CommandHandler(self.name, self.start)],
            allow_reentry=True,
            run_async=True))

        self.add_handler(CallbackQueryHandler(
            self.execute_trade_callback,
            run_async=True))

    @TGBFPlugin.private
    @TGBFPlugin.send_typing
    def start(self, update: Update, context: CallbackContext):
        context.user_data.clear()

        # No arguments --> show usage
        if not context.args:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return ConversationHandler.END

        context.user_data["lamden"] = Connect()
        context.user_data["contract"] = self.config.get("contract")

        # Create new offer
        if context.args[0].strip().lower() == "create":
            update.message.reply_text(
                "1) Enter <b>contract name</b> of token to <b>SELL</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=self.cancel_keyboard())
            return self.OFFER_TOKEN

        # Handle all other arguments
        else:
            self.otc_callback(update, context)
            return ConversationHandler.END

    def offer_token(self, update: Update, context: CallbackContext):
        offer_token = update.message.text.strip().lower()
        node_url = context.user_data["lamden"].node_url

        message = update.message.reply_text(f"{emo.HOURGLASS} Retrieving data...")

        try:
            url = f"{node_url}/contracts/{offer_token}/metadata"
            res = requests.get(url, params={"key": "token_symbol"})
            context.user_data["offer_token_symbol"] = res.json()["value"]
        except Exception as e:
            msg = f"{emo.ERROR} Can't retrieve token info. Enter contract name again"
            logging.error(f"Can't retrieve token info for '{offer_token}': {e}")
            update.message.reply_text(msg)
            return self.OFFER_TOKEN

        message.delete()

        context.user_data["offer_token"] = offer_token
        msg = "2) Enter <b>amount</b> to <b>SELL</b>"
        update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=self.cancel_keyboard())
        return self.OFFER_AMOUNT

    def offer_amount(self, update: Update, context: CallbackContext):
        try:
            context.user_data["offer_amount"] = float(update.message.text)
        except:
            msg = f"{emo.ERROR} Provided amount not valid, try again"
            update.message.reply_text(msg)
            return

        # --- TEMP ---
        # TODO: Remove temporal fix
        if not float(update.message.text).is_integer():
            msg = f"{emo.ERROR} Sorry for the inconvenience but currently the amount needs to be an Integer"
            update.message.reply_text(msg)
            return
        # --- TEMP ---

        msg = "3) Enter <b>contract name</b> of token to <b>RECEIVE</b>"
        update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=self.cancel_keyboard())
        return self.TAKE_TOKEN

    def take_token(self, update: Update, context: CallbackContext):
        take_token = update.message.text.strip().lower()
        node_url = context.user_data["lamden"].node_url

        message = update.message.reply_text(f"{emo.HOURGLASS} Retrieving data...")

        try:
            url = f"{node_url}/contracts/{take_token}/metadata"
            res = requests.get(url, params={"key": "token_symbol"})
            context.user_data["take_token_symbol"] = res.json()["value"]
        except Exception as e:
            msg = f"{emo.ERROR} Can't retrieve token info. Enter contract name again"
            logging.error(f"Can't retrieve token info for '{take_token}': {e}")
            update.message.reply_text(msg)
            return self.TAKE_TOKEN

        message.delete()

        context.user_data["take_token"] = update.message.text.lower()
        msg = "4) Enter <b>amount</b> to <b>RECEIVE</b>"
        update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=self.cancel_keyboard())
        return self.TAKE_AMOUNT

    def take_amount(self, update: Update, context: CallbackContext):
        try:
            context.user_data["take_amount"] = float(update.message.text)
        except:
            msg = f"{emo.ERROR} Provided amount not valid, try again"
            update.message.reply_text(msg)
            return

        # --- TEMP ---
        # TODO: Remove temporal fix
        if not float(update.message.text).is_integer():
            msg = f"{emo.ERROR} Sorry for the inconvenience but currently the amount needs to be an Integer"
            update.message.reply_text(msg)
            return
        # --- TEMP ---

        offer_amount = context.user_data["offer_amount"]
        offer_amount = int(offer_amount) if offer_amount.is_integer() else offer_amount

        take_amount = context.user_data["take_amount"]
        take_amount = int(take_amount) if take_amount.is_integer() else take_amount

        if context.user_data['offer_token_symbol']:
            offer_symbol = context.user_data['offer_token_symbol']
        else:
            offer_symbol = "TAU"

        if context.user_data['take_token_symbol']:
            take_symbol = context.user_data['take_token_symbol']
        else:
            take_symbol = "TAU"

        msg = f"SELL {offer_amount} {offer_symbol}\n" \
              f"({context.user_data['offer_token']})\n\n" \
              f"FOR {take_amount} {take_symbol}\n" \
              f"({context.user_data['take_token']})\n"

        node_url = context.user_data["lamden"].node_url
        contract = context.user_data["contract"]

        url = f"{node_url}/contracts/{contract}/fee"

        try:
            res = requests.get(url)
        except Exception as e:
            logging.error(f"Error retrieving OTC fee: {e}")
            update.message.reply_text(f"{emo.ERROR} {e}")
            return

        if "error" in res.json():
            msg = f"{emo.ERROR} Can't retrieve fee details: {res.json()['error']}"
            update.message.reply_text(msg)
            return

        fee = res.json()["value"]["__fixed__"]
        context.user_data["fee"] = fee

        fee_int = int(float(fee)) if float(fee).is_integer() else fee
        confirm = f"5) Confirm to send {offer_amount} {offer_symbol} + {fee_int}% fee"

        update.message.reply_text(
            f"<code>{msg}</code>\n{confirm}",
            reply_markup=self.confirm_keyboard(),
            parse_mode=ParseMode.HTML)

        return self.SUMMARY

    def summary(self, update: Update, context: CallbackContext):
        msg = f"{emo.HOURGLASS} Submitting OTC trade..."
        message = update.message.reply_text(msg)

        contract = context.user_data["contract"]

        wallet = self.get_wallet(update.effective_user.id)
        lamden = Connect(wallet)

        kwargs = {
            "offer_token": context.user_data["offer_token"],
            "offer_amount": context.user_data["offer_amount"],
            "take_token": context.user_data["take_token"],
            "take_amount": context.user_data["take_amount"]
        }

        # --- TEMP ---
        # TODO: Remove temporal fix
        kwargs = {
            "offer_token": context.user_data["offer_token"],
            "offer_amount": int(context.user_data["offer_amount"]),
            "take_token": context.user_data["take_token"],
            "take_amount": int(context.user_data["take_amount"])
        }
        # --- TEMP ---

        try:
            # Check if contract is approved to spend users token
            approved = lamden.get_approved_amount(
                contract=contract,
                token=context.user_data["offer_token"])

            approved = approved["value"] if "value" in approved else 0
            approved = approved if approved is not None else 0

            token = context.user_data["offer_token"]
            logging.info(f"Approved amount of {token} for {contract}: {approved}")

            # Approving
            if context.user_data["offer_amount"] > float(approved):
                app = lamden.approve_contract(
                    contract=contract,
                    token=context.user_data["offer_token"])

                logging.info(f"Approved {contract}: {app}")
        except Exception as e:
            logging.error(f"Error approving contract {contract}: {e}")

            message.delete()
            update.message.reply_text(
                f"{emo.ERROR} {e}",
                parse_mode=ParseMode.HTML,
                reply_markup=ReplyKeyboardRemove())

            return ConversationHandler.END

        logging.info(f"Creating offer: {kwargs}")

        try:
            # Call OTC contract
            ret = lamden.post_transaction(
                stamps=200,
                contract=contract,
                function="make_offer",
                kwargs=kwargs)
        except Exception as e:
            logging.error(f"Error calling 'create_offer' on {contract}: {e}")

            message.delete()
            update.message.reply_text(
                f"{emo.ERROR} {e}",
                parse_mode=ParseMode.HTML,
                reply_markup=ReplyKeyboardRemove())

            return ConversationHandler.END

        logging.info(f"Executed 'create_offer' on {contract}: {ret}")

        if "error" in ret:
            logging.error(f"Error calling 'create_offer' on {contract}: {ret['error']}")

            message.delete()
            update.message.reply_text(
                f"{emo.ERROR} {ret['error']}",
                parse_mode=ParseMode.HTML,
                reply_markup=ReplyKeyboardRemove())

            return ConversationHandler.END

        # Get transaction hash
        tx_hash = ret["hash"]

        # Wait for transaction to be completed
        success, result = lamden.tx_succeeded(tx_hash)

        if not success:
            logging.error(f"Tx 'create_offer' on {contract} not successful: {result}")

            message.delete()
            update.message.reply_text(
                f"{emo.ERROR} {result}",
                parse_mode=ParseMode.HTML,
                reply_markup=ReplyKeyboardRemove())

            return ConversationHandler.END

        offer_id = result["result"].replace("'", "")

        trade_url = f"{lamden.explorer_url}/transactions/{tx_hash}"
        trade_msg = f'{emo.DONE} <a href="{trade_url}">Offer submitted</a>'

        message.delete()
        update.message.reply_text(
            f"{trade_msg}\n\n<code>{offer_id}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=ReplyKeyboardRemove())

        return ConversationHandler.END

    def cancel(self, update: Update, context: CallbackContext):
        msg = f"{emo.STOP} Canceled OTC trade creation"
        update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    @TGBFPlugin.private
    @TGBFPlugin.send_typing
    def otc_callback(self, update: Update, context: CallbackContext):
        contract = self.config.get("contract")
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

        logging.info(f"Details for ID {otc_id}: {otc}")

        context.user_data["otc"] = otc
        context.user_data["otc_id"] = otc_id
        context.user_data["lamden"] = lamden
        context.user_data["contract"] = contract
        context.user_data["confirmed"] = False

        if isinstance(otc['offer_amount'], dict):
            if '__fixed__' in otc['offer_amount']:
                offer_amount = float(otc['offer_amount']['__fixed__'])
        else:
            offer_amount = int(otc['offer_amount'])

        if isinstance(offer_amount, float):
            offer_amount = int(offer_amount) if offer_amount.is_integer() else offer_amount

        if isinstance(otc['take_amount'], dict):
            if '__fixed__' in otc['take_amount']:
                take_amount = float(otc['take_amount']['__fixed__'])
        else:
            take_amount = int(otc['take_amount'])

        if isinstance(take_amount, float):
            take_amount = int(take_amount) if take_amount.is_integer() else take_amount

        node_url = Connect().node_url

        try:
            url = f"{node_url}/contracts/{otc['take_token']}/metadata"
            res = requests.get(url, params={"key": "token_symbol"})
            take_symbol = res.json()["value"]
        except Exception as e:
            logging.error(f"Can't retrieve token info for '{otc['take_token']}': {e}")
            msg = f"{emo.ERROR} Can't retrieve token info for {otc['take_token']}"
            update.message.reply_text(msg)
            return

        try:
            url = f"{node_url}/contracts/{otc['offer_token']}/metadata"
            res = requests.get(url, params={"key": "token_symbol"})
            offer_symbol = res.json()["value"]
        except Exception as e:
            logging.error(f"Can't retrieve token info for '{otc['offer_token']}': {e}")
            msg = f"{emo.ERROR} Can't retrieve token info for {otc['offer_token']}"
            update.message.reply_text(msg)
            return

        take_symbol = take_symbol if take_symbol else "TAU"
        offer_symbol = offer_symbol if offer_symbol else "TAU"

        context.user_data["take_symbol"] = take_symbol
        context.user_data["offer_symbol"] = offer_symbol

        msg = f"SELL {offer_amount} {offer_symbol}\n" \
              f"({otc['offer_token']})\n\n" \
              f"FOR {take_amount} {take_symbol}\n" \
              f"({otc['take_token']})\n"

        # Check if trade was canceled
        if otc["state"] == "CANCELED":
            ex = f"{emo.INFO} Trade was canceled"
            update.message.reply_text(
                f"<code>{msg}</code>\n\n{ex}",
                parse_mode=ParseMode.HTML)
            return

        # Check if trade was executed
        if otc["state"] == "EXECUTED":
            ex = f"{emo.INFO} Trade was executed"
            update.message.reply_text(
                f"<code>{msg}</code>\n\n{ex}",
                parse_mode=ParseMode.HTML)
            return

        # If user is creator then show "Cancel offer"
        if otc["maker"] == wallet.verifying_key:
            context.user_data["cancel"] = True

            update.message.reply_text(
                f"<code>{msg}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=self.button_callback("Cancel offer"))

        # Show "Take offer"
        else:
            context.user_data["cancel"] = False

            fee = float(otc['fee']['__fixed__'])
            fee = int(fee) if fee.is_integer() else fee
            fee = f"Excluding {fee}% Taker fee"

            update.message.reply_text(
                f"<code>{msg}\n{fee}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=self.button_callback("Take offer"))

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
                reply_markup=self.button_callback("CONFIRM TO EXECUTE"))

        # User already confirmed
        else:
            otc = context.user_data["otc"]
            otc_id = context.user_data["otc_id"]
            lamden = context.user_data["lamden"]
            contract = context.user_data["contract"]

            # Offer needs to be canceled
            if context.user_data["cancel"]:
                message.edit_text(
                    f"<code>{message.text}</code>\n\n{emo.HOURGLASS} Canceling trade ...",
                    parse_mode=ParseMode.HTML)

                try:
                    # Call OTC contract
                    ret = lamden.post_transaction(
                        stamps=80,
                        contract=contract,
                        function="cancel_offer",
                        kwargs={"offer_id": otc_id})
                except Exception as e:
                    logging.error(f"Error calling 'cancel_offer' on {contract}: {e}")
                    message.edit_text(
                        f"<code>{message.text}</code>\n\n{emo.ERROR} {e}",
                        parse_mode=ParseMode.HTML)
                    return

                logging.info(f"Called 'cancel_offer' on {contract}: {ret}")

                if "error" in ret:
                    logging.error(f"Error calling 'cancel_offer' on {contract}: {ret['error']}")
                    message.edit_text(
                        f"<code>{message.text}</code>\n\n{emo.ERROR} {ret['error']}",
                        parse_mode=ParseMode.HTML)
                    return

                # Get transaction hash
                tx_hash = ret["hash"]

                # Wait for transaction to be completed
                success, result = lamden.tx_succeeded(tx_hash)

                if not success:
                    logging.error(f"Tx 'cancel_offer' on {contract} not successful: {result}")
                    message.edit_text(
                        f"<code>{message.text}</code>\n\n{emo.ERROR} {result}",
                        parse_mode=ParseMode.HTML)
                    return

                trade_url = f"{lamden.explorer_url}/transactions/{tx_hash}"
                trade_msg = f'{emo.DONE} <a href="{trade_url}">Trade canceled</a>'

                message.edit_text(
                    f"<code>{message.text}</code>\n\n{trade_msg}",
                    parse_mode=ParseMode.HTML)

                msg = f"{emo.DONE} Trade canceled"
                context.bot.answer_callback_query(update.callback_query.id, msg)

            # Offer needs to be executed
            else:
                message.edit_text(
                    f"<code>{message.text}</code>\n\n{emo.HOURGLASS} Executing trade ...",
                    parse_mode=ParseMode.HTML)

                try:
                    # Check if contract is approved to spend TAU
                    approved = lamden.get_approved_amount(
                        contract=contract,
                        token=otc["take_token"])

                    approved = approved["value"] if "value" in approved else 0
                    approved = approved if approved is not None else 0

                    logging.info(f"Approved amount of TAU for {contract}: {approved}")

                    # Calculate fee amount
                    fee = float(otc["fee"]['__fixed__'])

                    if isinstance(otc["take_amount"], dict):
                        if ['__fixed__'] in otc["take_amount"]:
                            amount = float(otc["take_amount"]['__fixed__'])
                    else:
                        amount = int(otc["take_amount"])

                    fee_amount = amount / 100 * fee

                    # Approving
                    if (amount + fee_amount) > float(approved):
                        app = lamden.approve_contract(
                            contract=contract,
                            token=otc["take_token"])

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
                        function="take_offer",
                        kwargs={"offer_id": otc_id})
                except Exception as e:
                    logging.error(f"Error calling 'take_offer' on {contract}: {e}")
                    message.edit_text(
                        f"<code>{message.text}</code>\n\n{emo.ERROR} {e}",
                        parse_mode=ParseMode.HTML)
                    return

                logging.info(f"Called 'take_offer' on {contract}: {ret}")

                if "error" in ret:
                    logging.error(f"Error calling 'take_offer' on {contract}: {ret['error']}")
                    message.edit_text(
                        f"<code>{message.text}</code>\n\n{emo.ERROR} {ret['error']}",
                        parse_mode=ParseMode.HTML)
                    return

                # Get transaction hash
                tx_hash = ret["hash"]

                # Wait for transaction to be completed
                success, result = lamden.tx_succeeded(tx_hash)

                if not success:
                    logging.error(f"Tx 'take_offer' on {contract} not successful: {result}")
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

    def button_callback(self, label: str):
        menu = utl.build_menu([InlineKeyboardButton(label, callback_data=self.name)])
        return InlineKeyboardMarkup(menu, resize_keyboard=True)

    def cancel_keyboard(self):
        menu = utl.build_menu([KeyboardButton(self.CANCEL)], n_cols=1)
        return ReplyKeyboardMarkup(menu, resize_keyboard=True)

    def confirm_keyboard(self):
        menu = utl.build_menu([KeyboardButton(self.CANCEL), KeyboardButton(self.CONFIRM)], n_cols=2)
        return ReplyKeyboardMarkup(menu, resize_keyboard=True)
