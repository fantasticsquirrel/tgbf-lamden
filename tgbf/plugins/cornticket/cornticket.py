import os
import logging
import tgbf.emoji as emo
import tgbf.utils as utl

from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


# TODO: Add possibility to start next round at a later time and not directly
class Cornticket(TGBFPlugin):

    TOKEN_CONTRACT = "con_bitcorn"
    TOKEN_SYMBOL = "CORN"

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.cornticket_callback,
            run_async=True))

        self.add_handler(CallbackQueryHandler(
            self.button_callback,
            run_async=True))

    @TGBFPlugin.blacklist
    @TGBFPlugin.send_typing
    def cornticket_callback(self, update: Update, context: CallbackContext):
        if len(context.args) == 1 and context.args[0].lower() == "balance":
            contract = self.config.get("contract")

            lamden = Connect()

            tau_balance = lamden.get_contract_variable(contract, "tau_balance")
            tau_balance = tau_balance["value"] if "value" in tau_balance else 0
            tau_balance = float(str(tau_balance)) if tau_balance else float("0")
            tau_balance = f"{int(tau_balance):,}"

            corn_balance = lamden.get_contract_variable(contract, "corn_balance")
            corn_balance = corn_balance["value"] if "value" in corn_balance else 0
            corn_balance = float(str(corn_balance)) if corn_balance else float("0")
            corn_balance = f"{int(corn_balance):,}"

            user_count = len(lamden.get_contract_variable(contract, "user_list")["value"])

            max_entries = lamden.get_contract_variable(contract, "max_entries")
            max_entries = max_entries["value"] if "value" in max_entries else 0

            update.message.reply_text(
                text=f"<code>"
                     f"CORN Ticket Balance\n"
                     f"TAU:  {tau_balance}\n"
                     f"CORN: {corn_balance}\n\n"
                     f"Tickets\n"
                     f"Total:     {max_entries}\n"
                     f"Available: {int(max_entries) - int(user_count)}"
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
                    stamps=150,
                    contract=contract,
                    function=function,
                    kwargs={}
                )
            except Exception as e:
                logging.error(f"Error calling cornticket contract (draw_winner): {e}")
                update.message.reply_text(f"{emo.ERROR} {e}")
                return

            logging.info(f"Executed cornticket contract: {ticket}")

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

            last_won_corn = lamden.get_contract_variable(contract, "last_won_corn")
            last_won_corn = last_won_corn["value"] if "value" in last_won_corn else 0
            last_won_corn = float(str(last_won_corn)) if last_won_corn else float("0")
            last_won_corn = f"{int(last_won_corn):,}"

            last_reserve_corn = lamden.get_contract_variable(contract, "last_reserve_corn")
            last_reserve_corn = last_reserve_corn["value"] if "value" in last_reserve_corn else 0
            last_reserve_corn = float(str(last_reserve_corn)) if last_reserve_corn else float("0")
            last_reserve_corn = f"{int(last_reserve_corn):,}"

            total_won_tau = lamden.get_contract_variable(contract, "total_won_tau")
            total_won_tau = total_won_tau["value"] if "value" in total_won_tau else 0
            total_won_tau = float(str(total_won_tau)) if total_won_tau else float("0")
            total_won_tau = f"{int(total_won_tau):,}"

            total_won_corn = lamden.get_contract_variable(contract, "total_won_corn")
            total_won_corn = total_won_corn["value"] if "value" in total_won_corn else 0
            total_won_corn = float(str(total_won_corn)) if total_won_corn else float("0")
            total_won_corn = f"{int(total_won_corn):,}"

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
            br_link = f'<a href="https://www.tauhq.com/addresses/96dae3b6213fb80eac7c6f4fa0fd26f34022741c56773107b20199cb43f5ed62">ADDRESS</a>'
            lp_link = f'<a href="https://rocketswap.exchange/#/pool-add/con_bitcorn">add your winnings to the LP</a>'

            msg = f"WINNER\n" \
                  f"{user}\n" \
                  f"{ad_link}\n\n" \
                  f"AMOUNT WON\n" \
                  f"<code>TAU:  {last_won_tau}</code>\n" \
                  f"<code>CORN: {last_won_corn}</code>\n\n" \
                  f"AMOUNT SENT TO GOLD RESERVE ({br_link})\n" \
                  f"<code>CORN: {last_reserve_corn}</code>\n\n" \
                  f"TOTAL AMOUNT WON TO DATE\n" \
                  f"<code>TAU:  {total_won_tau}</code>\n" \
                  f"<code>CORN: {total_won_corn}</code>\n\n" \
                  f"TOTAL DEV FUND AMOUNT\n" \
                  f"<code>TAU:  {total_dev_fund}</code>\n\n" \
                  f"{tx_link}\n\n" \
                  f"Hey, why not {lp_link} to earn more CORN?"

            winner_video_path = os.path.join(self.get_res_path(), "cornticket_winner.mp4")
            update.message.reply_video(open(winner_video_path, "rb"), caption=msg, parse_mode=ParseMode.HTML)
            return

        cal_msg = f"{emo.HOURGLASS} Calculating CORN amount..."
        gt_path = os.path.join(self.get_res_path(), "cornticket.jpg")
        message = update.message.reply_photo(open(gt_path, "rb"), caption=cal_msg)

        lamden = Connect()

        corn_price = lamden.get_contract_variable(
            "con_rocketswap_official_v1_1",
            "prices",
            self.TOKEN_CONTRACT
        )

        corn_price = corn_price["value"] if "value" in corn_price else 0
        corn_price = float(str(corn_price)) if corn_price else float("0")

        amount_tau = self.config.get("amount_tau")
        amount_corn = amount_tau / corn_price

        context.user_data["amount_tau"] = amount_tau
        context.user_data["amount_corn"] = amount_corn

        message.edit_caption(
            f"Pay TAU and CORN to buy a TICKET:\n"
            f"<code>"
            f"TAU:  {amount_tau}\n"
            f"CORN: {int(amount_corn)+1:,}\n"
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
            tauhq_link = f'<a href="https://www.tauhq.com/tokens/con_bitcorn">CORN Token on TauHQ</a>'

            update.callback_query.message.edit_caption(
                f"{self.get_resource('cornticket.md')}\n\n{tauhq_link}",
                parse_mode=ParseMode.HTML)

            msg = f"{emo.BOOKS} Happy reading!"
            context.bot.answer_callback_query(update.callback_query.id, msg)
            return

        elif action == "SEND":
            if "amount_tau" not in context.user_data:
                msg = f"{emo.ERROR} Message expired"
                context.bot.answer_callback_query(update.callback_query.id, msg)
                return
            if "amount_corn" not in context.user_data:
                msg = f"{emo.ERROR} Message expired"
                context.bot.answer_callback_query(update.callback_query.id, msg)
                return

            amount_tau = context.user_data["amount_tau"]
            amount_corn = context.user_data["amount_corn"]

            contract = self.config.get("contract")
            function = self.config.get("function")

            message = update.callback_query.message
            message.edit_caption(f"{emo.HOURGLASS} Buying ticket...")

            usr_id = update.effective_user.id
            wallet = self.get_wallet(usr_id)
            lamden = Connect(wallet)

            try:
                # Check if contract is approved to spend CORN
                approved = lamden.get_approved_amount(contract, token=self.TOKEN_CONTRACT)
                approved = approved["value"] if "value" in approved else 0
                approved = approved if approved is not None else 0

                msg = f"Approved amount of {self.TOKEN_SYMBOL} for {contract}: {approved}"
                logging.info(msg)

                if amount_corn > float(approved):
                    app = lamden.approve_contract(contract, token=self.TOKEN_CONTRACT)
                    msg = f"Approved {contract}: {app}"
                    logging.info(msg)
            except Exception as e:
                logging.error(f"Error approving cornticket contract: {e}")
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
                logging.error(f"Error approving cornticket contract: {e}")
                message.edit_caption(f"{emo.ERROR} {e}")
                return

            try:
                # Call contract
                ticket = lamden.post_transaction(
                    stamps=200,
                    contract=contract,
                    function=function,
                    kwargs={}
                )
            except Exception as e:
                logging.error(f"Error calling cornticket contract: {e}")
                message.edit_caption(f"{emo.ERROR} {e}")
                return

            logging.info(f"Executed cornticket contract: {ticket}")

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
                f"Thanks for entering CORNTICKET. You are entry {cur_users}/{max_users}\n{ex_link}",
                parse_mode=ParseMode.HTML)

            msg = f"{emo.TICKET} Ticket bought"
            context.bot.answer_callback_query(update.callback_query.id, msg)

    def get_buttons(self, user_id):
        menu = utl.build_menu([
            InlineKeyboardButton("Send TAU & CORN", callback_data=f"{self.name}|{user_id}|SEND"),
            InlineKeyboardButton("Read How-To", callback_data=f"{self.name}|{user_id}|READ")
        ])
        return InlineKeyboardMarkup(menu, resize_keyboard=True)
