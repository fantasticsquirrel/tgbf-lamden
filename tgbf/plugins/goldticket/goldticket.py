import os
import logging
import tgbf.emoji as emo
import tgbf.utils as utl

from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


# TODO: Add possibility to start next round at a later time and not directly
class Goldticket(TGBFPlugin):

    TOKEN_CONTRACT = "con_gold_contract"
    TOKEN_SYMBOL = "GOLD"

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.goldticket_callback,
            run_async=True))

        self.add_handler(CallbackQueryHandler(
            self.button_callback,
            run_async=True))

    @TGBFPlugin.blacklist
    @TGBFPlugin.send_typing
    def goldticket_callback(self, update: Update, context: CallbackContext):
        if len(context.args) == 1 and context.args[0].lower() == "balance":
            contract = self.config.get("contract")

            lamden = Connect()

            tau_balance = lamden.get_contract_variable(contract, "tau_balance")

            tau_balance = tau_balance["value"] if "value" in tau_balance else 0
            tau_balance = float(str(tau_balance)) if tau_balance else float("0")
            tau_balance = f"{int(tau_balance):,}"

            gold_balance = lamden.get_contract_variable(contract, "gold_balance")

            gold_balance = gold_balance["value"] if "value" in gold_balance else 0
            gold_balance = float(str(gold_balance)) if gold_balance else float("0")
            gold_balance = f"{int(gold_balance):,}"

            update.message.reply_text(
                text=f"<code>"
                     f"GOLD Ticket Balance:\n"
                     f"TAU:  {tau_balance}\n"
                     f"GOLD: {gold_balance}"
                     f"</code>",
                parse_mode=ParseMode.HTML
            )

            return

        # TODO: Add confirmation for drawing the winner
        if len(context.args) == 1 and context.args[0].lower() == "draw_winner":
            usr_id = update.effective_user.id

            if usr_id not in self.config.get("admins"):
                return

            wallet = self.get_wallet(usr_id)
            lamden = Connect(wallet)

            contract = self.config.get("contract")
            function = "draw_winner"

            try:
                # Call contract
                ticket = lamden.post_transaction(
                    stamps=100,
                    contract=contract,
                    function=function,
                    kwargs={}
                )
            except Exception as e:
                logging.error(f"Error calling goldticket contract (draw_winner): {e}")
                update.message.reply_text(f"{emo.ERROR} {e}")
                return

            logging.info(f"Executed goldticket contract: {ticket}")

            if "error" in ticket:
                logging.error(f"Goldticket contract (draw_winner) returned error: {ticket['error']}")
                update.message.reply_text(f"{emo.ERROR} {ticket['error']}")
                return

            # Get transaction hash
            tx_hash = ticket["hash"]

            # Wait for transaction to be completed
            success, result = lamden.tx_succeeded(tx_hash)

            if not success:
                logging.error(f"Goldticket (draw_winner) transaction not successful: {result}")
                update.message.reply_text(f"{emo.ERROR} {result}")
                return

            winner_address = result["result"].replace("'", "")

            last_won_tau = lamden.get_contract_variable(contract, "last_won_tau")
            last_won_tau = last_won_tau["value"] if "value" in last_won_tau else 0
            last_won_tau = float(str(last_won_tau)) if last_won_tau else float("0")
            last_won_tau = f"{int(last_won_tau):,}"

            last_won_gold = lamden.get_contract_variable(contract, "last_won_gold")
            last_won_gold = last_won_gold["value"] if "value" in last_won_gold else 0
            last_won_gold = float(str(last_won_gold)) if last_won_gold else float("0")
            last_won_gold = f"{int(last_won_gold):,}"

            last_burned_gold = lamden.get_contract_variable(contract, "last_burned_gold")
            last_burned_gold = last_burned_gold["value"] if "value" in last_burned_gold else 0
            last_burned_gold = float(str(last_burned_gold)) if last_burned_gold else float("0")
            last_burned_gold = f"{int(last_burned_gold):,}"

            total_won_tau = lamden.get_contract_variable(contract, "total_won_tau")
            total_won_tau = total_won_tau["value"] if "value" in total_won_tau else 0
            total_won_tau = float(str(total_won_tau)) if total_won_tau else float("0")
            total_won_tau = f"{int(total_won_tau):,}"

            total_won_gold = lamden.get_contract_variable(contract, "total_won_gold")
            total_won_gold = total_won_gold["value"] if "value" in total_won_gold else 0
            total_won_gold = float(str(total_won_gold)) if total_won_gold else float("0")
            total_won_gold = f"{int(total_won_gold):,}"

            total_dev_fund = lamden.get_contract_variable(contract, "dev_tau")
            total_dev_fund = total_dev_fund["value"] if "value" in total_dev_fund else 0
            total_dev_fund = float(str(total_dev_fund)) if total_dev_fund else float("0")
            total_dev_fund = f"{int(total_dev_fund):,}"

            sql = self.get_global_resource("select_user_id.sql")
            res = self.execute_global_sql(sql, winner_address)

            if res["data"]:
                user = context.bot.get_chat(int(res["data"][0][0]))
                if user:
                    user = "@" + user.username if user.username else user.first_name
                else:
                    user = ""
            else:
                user = ""

            first = winner_address[0:6]
            last = winner_address[len(winner_address)-6:len(winner_address)]

            tx_link = f'<a href="{lamden.explorer_url}/transactions/{tx_hash}">View Transaction on Explorer</a>'
            ad_link = f'<a href="{lamden.explorer_url}/addresses/{winner_address}">{first}...{last}</a>'
            br_link = f'<a href="https://www.tauhq.com/addresses/0000000000000BURN0000000000000">ADDRESS</a>'

            msg = f"WINNER\n" \
                  f"{user}\n" \
                  f"{ad_link}\n\n" \
                  f"AMOUNT WON\n" \
                  f"<code>TAU:  {last_won_tau}</code>\n" \
                  f"<code>GOLD: {last_won_gold}</code>\n\n" \
                  f"AMOUNT BURNED ({br_link})\n" \
                  f"<code>GOLD: {last_burned_gold}</code>\n\n" \
                  f"TOTAL AMOUNT WON TO DATE\n" \
                  f"<code>TAU:  {total_won_tau}</code>\n" \
                  f"<code>GOLD: {total_won_gold}</code>\n\n" \
                  f"TOTAL DEV FUND AMOUNT\n" \
                  f"<code>TAU:  {total_dev_fund}</code>\n\n" \
                  f"{tx_link}"

            winner_video_path = os.path.join(self.get_res_path(), "goldticket_winner.mp4")
            update.message.reply_video(open(winner_video_path, "rb"), caption=msg, parse_mode=ParseMode.HTML)
            return

        cal_msg = f"{emo.HOURGLASS} Calculating GOLD amount..."
        gt_path = os.path.join(self.get_res_path(), "goldticket.jpg")
        message = update.message.reply_photo(open(gt_path, "rb"), caption=cal_msg)

        lamden = Connect()

        gold_price = lamden.get_contract_variable(
            "con_rocketswap_official_v1_1",
            "prices",
            self.TOKEN_CONTRACT
        )

        gold_price = gold_price["value"] if "value" in gold_price else 0
        gold_price = float(str(gold_price)) if gold_price else float("0")

        amount_tau = self.config.get("amount_tau")
        amount_gold = amount_tau / gold_price

        context.user_data["amount_tau"] = amount_tau
        context.user_data["amount_gold"] = amount_gold

        message.edit_caption(
            f"Pay TAU and GOLD to buy a TICKET:\n"
            f"<code>"
            f"TAU:  {amount_tau}\n"
            f"GOLD: {int(amount_gold)+1:,}\n"
            f"</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=self.get_buttons(update.effective_user.id))

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

        action = data_list[2]
        if action == "READ":
            tauhq_link = f'<a href="https://www.tauhq.com/tokens/con_gold_contract">GOLD Token on TauHQ</a>'

            update.callback_query.message.edit_caption(
                f"{self.get_resource('goldticket.md')}\n\n{tauhq_link}",
                parse_mode=ParseMode.HTML)

            msg = f"{emo.BOOKS} Happy reading!"
            context.bot.answer_callback_query(update.callback_query.id, msg)
            return

        elif action == "SEND":
            if "amount_tau" not in context.user_data:
                msg = f"{emo.ERROR} Message expired"
                context.bot.answer_callback_query(update.callback_query.id, msg)
                return
            if "amount_gold" not in context.user_data:
                msg = f"{emo.ERROR} Message expired"
                context.bot.answer_callback_query(update.callback_query.id, msg)
                return

            amount_tau = context.user_data["amount_tau"]
            amount_gold = context.user_data["amount_gold"]

            contract = self.config.get("contract")
            function = self.config.get("function")

            message = update.callback_query.message
            message.edit_caption(f"{emo.HOURGLASS} Buying ticket...")

            usr_id = update.effective_user.id
            wallet = self.get_wallet(usr_id)
            lamden = Connect(wallet)

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
                logging.error(f"Error approving goldticket contract: {e}")
                message.edit_caption(f"{emo.ERROR} {e}")
                return

            try:
                # Check if contract is approved to spend TAU
                approved = lamden.get_approved_amount(contract, token="currency")
                approved = approved["value"] if "value" in approved else 0
                approved = approved if approved is not None else 0

                msg = f"Approved amount of TAU for {contract}: {approved}"
                logging.info(msg)

                if amount_tau > float(approved):
                    app = lamden.approve_contract(contract, token="currency")
                    msg = f"Approved {contract}: {app}"
                    logging.info(msg)
            except Exception as e:
                logging.error(f"Error approving goldticket contract: {e}")
                message.edit_caption(f"{emo.ERROR} {e}")
                return

            try:
                # Call contract
                ticket = lamden.post_transaction(
                    stamps=100,
                    contract=contract,
                    function=function,
                    kwargs={}
                )
            except Exception as e:
                logging.error(f"Error calling goldticket contract: {e}")
                message.edit_caption(f"{emo.ERROR} {e}")
                return

            logging.info(f"Executed goldticket contract: {ticket}")

            if "error" in ticket:
                logging.error(f"Goldticket contract returned error: {ticket['error']}")
                message.edit_caption(f"{emo.ERROR} {ticket['error']}")
                return

            # Get transaction hash
            tx_hash = ticket["hash"]

            # Wait for transaction to be completed
            success, result = lamden.tx_succeeded(tx_hash)

            if not success:
                logging.error(f"Goldticket transaction not successful: {result}")
                message.edit_caption(f"{emo.ERROR} {result}")
                return

            ex_link = f'<a href="{lamden.explorer_url}/transactions/{tx_hash}">View Transaction on Explorer</a>'

            cur_users = len(lamden.get_contract_variable(contract, "user_list")["value"])
            max_users = lamden.get_contract_variable(contract, "max_entries")["value"]

            message.edit_caption(
                f"Thanks entering GOLDTICKET. You are entry {cur_users}/{max_users}\n{ex_link}",
                parse_mode=ParseMode.HTML)

            msg = f"{emo.TICKET} Ticket bought"
            context.bot.answer_callback_query(update.callback_query.id, msg)

    def get_buttons(self, user_id):
        menu = utl.build_menu([
            InlineKeyboardButton("Send TAU & GOLD", callback_data=f"{self.name}|{user_id}|SEND"),
            InlineKeyboardButton("Read How-To", callback_data=f"{self.name}|{user_id}|READ")
        ])
        return InlineKeyboardMarkup(menu, resize_keyboard=True)
