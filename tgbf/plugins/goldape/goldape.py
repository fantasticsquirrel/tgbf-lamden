import os
import logging
import tgbf.emoji as emo
import tgbf.utils as utl

from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from tgbf.lamden.rocketswap import Rocketswap
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Goldape(TGBFPlugin):

    TOKEN_CONTRACT = "con_gold_contract"
    TOKEN_SYMBOL = "GOLD"

    def load(self):
        if not self.table_exists("listings"):
            sql = self.get_resource("create_listings.sql")
            self.execute_sql(sql)

        self.add_handler(CommandHandler(
            self.name,
            self.goldape_callback,
            run_async=True))

        self.add_handler(CallbackQueryHandler(
            self.button_callback,
            run_async=True))

        update_interval = self.config.get("update_interval")
        self.run_repeating(self.check_tokens, update_interval)

    @TGBFPlugin.send_typing
    def goldape_callback(self, update: Update, context: CallbackContext):
        if len(context.args) == 0:
            cal_msg = f"{emo.HOURGLASS} Calculating {self.TOKEN_SYMBOL} amount..."
            gt_path = os.path.join(self.get_res_path(), "goldape.jpg")
            message = update.message.reply_photo(open(gt_path, "rb"), caption=cal_msg)

            message.edit_caption(
                f"<b>{self.TOKEN_SYMBOL} Ape Listings</b>\n\n"
                f"Subscribe to the service by paying {self.get_amount_gold():,} {self.TOKEN_SYMBOL} "
                f"or unsubscribe to get % of your subscription amount back based on time "
                f"you were subscribed:\n\n"
                f"subscribed for <  30 days --> 30%\n"
                f"subscribed for <  90 days --> 50%\n"
                f"subscribed for < 120 days --> 70%\n"
                f"subscribed for > 120 days --> 80%\n"
                f"</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_buttons(update.effective_user.id))

    def check_tokens(self, context: CallbackContext):
        contract_list = list()

        listings = self.execute_sql(self.get_resource("select_listings.sql"))

        if listings and listings["data"]:
            for listing in listings["data"]:
                contract_list.append(listing[0])

        rs = Rocketswap()

        for market in rs.get_market_summaries_w_token():
            if market["contract_name"] not in contract_list:
                logging.info(f"New listing on Rocketswap found: {market}")

                token_info = rs.token(market["contract_name"])
                base_supply = token_info["token"]["base_supply"]

                try:
                    self.bot.updater.bot.send_message(
                        self.config.get("listing_chat_id"),
                        f"<b>NEW LISTING ON ROCKETSWAP</b>\n\n"
                        f"{market['token']['token_name']} ({market['token']['token_symbol']})\n\n"
                        f"Total Supply:\n"
                        f"{int(base_supply):,}\n\n"
                        f"Liquidity Reserves:\n"
                        f"<code>TAU: {float(market['reserves'][0]):,.8f}</code>\n"
                        f"<code>{market['token']['token_symbol']}: {float(market['reserves'][1]):,.8f}</code>\n\n"
                        f"Current Price:\n"
                        f"<code>{float(market['Last']):,.8f} TAU</code>",
                        parse_mode=ParseMode.HTML
                    )

                    self.execute_sql(self.get_resource("insert_listing.sql"), market["contract_name"])
                except Exception as e:
                    self.notify(f"Can't notify about new listing: {e}")

    def button_callback(self, update: Update, context: CallbackContext):
        data = update.callback_query.data

        if not data.startswith(self.name):
            return

        data_list = data.split("|")

        if not data_list:
            return

        if len(data_list) < 2:
            return

        if int(data_list[1]) != update.effective_user.id:
            return

        message = update.callback_query.message

        contract = self.config.get("contract")

        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet)

        action = data_list[2]

        # --- UNSUBSCRIBE ---
        if action == "UNSUB":
            message.edit_caption(f"{emo.HOURGLASS} Unsubscribing...")

            try:
                # Call contract
                ape = lamden.post_transaction(
                    stamps=70,
                    contract=contract,
                    function="unsubscribe",
                    kwargs={}
                )
            except Exception as e:
                logging.error(f"Error calling goldape contract: {e}")
                message.edit_caption(f"{emo.ERROR} {e}")
                return

            logging.info(f"Executed goldape contract: {ape}")

            if "error" in ape:
                logging.error(f"Goldape contract returned error: {ape['error']}")
                message.edit_caption(f"{emo.ERROR} {ape['error']}")
                return

            # Get transaction hash
            tx_hash = ape["hash"]

            # Wait for transaction to be completed
            success, result = lamden.tx_succeeded(tx_hash)

            if not success:
                logging.error(f"Goldape transaction not successful: {result}")
                message.edit_caption(f"{emo.ERROR} {result}")
                return

            gold_returned = result["result"]

            ex_link = f'<a href="{lamden.explorer_url}/transactions/{tx_hash}">View Transaction on Explorer</a>'

            message.edit_caption(
                f"You successfully unsubscribed from GOLD Ape Listings. "
                f"{int(gold_returned):,} GOLD was returned.\n{ex_link}",
                parse_mode=ParseMode.HTML)

            msg = f"{emo.DONE} Unsubscribed"
            context.bot.answer_callback_query(update.callback_query.id, msg)

        # --- SUBSCRIBE ---
        elif action == "SUB":
            message.edit_caption(f"{emo.HOURGLASS} Subscribing...")

            amount_gold = self.get_amount_gold()

            try:
                # Check if contract is approved to spend GOLD
                approved = lamden.get_approved_amount(contract, token=self.TOKEN_CONTRACT)
                approved = approved["value"] if "value" in approved else 0
                approved = approved if approved is not None else 0

                msg = f"Approved amount of {self.TOKEN_SYMBOL} for {contract}: {approved}"
                logging.info(msg)

                if amount_gold > float(approved):
                    app = lamden.approve_contract(contract, token=self.TOKEN_CONTRACT)
                    msg = f"Approved {contract}: {app}"
                    logging.info(msg)
            except Exception as e:
                logging.error(f"Error approving goldape contract: {e}")
                message.edit_caption(f"{emo.ERROR} {e}")
                return

            try:
                # Call contract
                ape = lamden.post_transaction(
                    stamps=70,
                    contract=contract,
                    function="subscribe",
                    kwargs={}
                )
            except Exception as e:
                logging.error(f"Error calling goldape contract: {e}")
                message.edit_caption(f"{emo.ERROR} {e}")
                return

            logging.info(f"Executed goldape contract: {ape}")

            if "error" in ape:
                logging.error(f"Goldape contract returned error: {ape['error']}")
                message.edit_caption(f"{emo.ERROR} {ape['error']}")
                return

            # Get transaction hash
            tx_hash = ape["hash"]

            # Wait for transaction to be completed
            success, result = lamden.tx_succeeded(tx_hash)

            if not success:
                logging.error(f"Goldape transaction not successful: {result}")
                message.edit_caption(f"{emo.ERROR} {result}")
                return

            ex_link = f'<a href="{lamden.explorer_url}/transactions/{tx_hash}">View Transaction on Explorer</a>'

            message.edit_caption(
                f"You successfully subscribed to GOLD Ape Listings. "
                f"You will receive an invite to a listing channel in a DM.\n{ex_link}",
                parse_mode=ParseMode.HTML)

            # TODO: Send channel invite to user

            msg = f"{emo.DONE} Subscribed & Invite sent"
            context.bot.answer_callback_query(update.callback_query.id, msg)

    def get_buttons(self, user_id):
        menu = utl.build_menu([
            InlineKeyboardButton("Subscribe", callback_data=f"{self.name}|{user_id}|SUB"),
            InlineKeyboardButton("Unsubscribe", callback_data=f"{self.name}|{user_id}|UNSUB")
        ])
        return InlineKeyboardMarkup(menu, resize_keyboard=True)

    def get_amount_gold(self):
        lamden = Connect()

        gold_price = lamden.get_contract_variable(
            "con_rocketswap_official_v1_1",
            "prices",
            self.TOKEN_CONTRACT
        )

        gold_price = gold_price["value"] if "value" in gold_price else 0
        gold_price = float(str(gold_price)) if gold_price else float("0")

        amount_tau = lamden.get_contract_variable(
            self.config.get("contract"),
            "tau_amount"
        )

        return amount_tau / gold_price
