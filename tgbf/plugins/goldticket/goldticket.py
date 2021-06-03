import logging
import tgbf.emoji as emo
import tgbf.utils as utl

from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin

# TODO: Make sure that only initiator can press buttons
# TODO: 40 participants
# TODO: Result should include amount of GOLD and TAU won and dev-fund
# TODO: Include banner
# TODO: Include link to https://www.tauhq.com/tokens/con_gold_contract
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

        cal_msg = f"{emo.HOURGLASS} Calculating GOLD amount..."
        message = update.message.reply_text(cal_msg)

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

        message.edit_text(
            f"<code>"
            f"Buy ticket by paying:\n"
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

        if int(data_list[1]) != update.effective_user.id:
            return

        action = data_list[2]
        if action == "READ":
            update.callback_query.message.edit_text(self.get_resource("goldticket.md"))

            msg = f"{emo.BOOKS} Happy reading!"
            context.bot.answer_callback_query(update.callback_query.id, msg)
            return

        elif action == "SEND":
            amount_tau = context.user_data["amount_tau"]
            amount_gold = context.user_data["amount_gold"]

            contract = self.config.get("contract")
            function = self.config.get("function")

            message = update.callback_query.message
            message.edit_text(f"{emo.HOURGLASS} Buying ticket...")

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
                message.edit_text(f"{emo.ERROR} {e}")
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
                message.edit_text(f"{emo.ERROR} {e}")
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
                message.edit_text(f"{emo.ERROR} {e}")
                return

            logging.info(f"Executed goldticket contract: {ticket}")

            if "error" in ticket:
                logging.error(f"Goldticket contract returned error: {ticket['error']}")
                message.edit_text(f"{emo.ERROR} {ticket['error']}")
                return

            # Get transaction hash
            tx_hash = ticket["hash"]

            # Wait for transaction to be completed
            success, result = lamden.tx_succeeded(tx_hash)

            if not success:
                logging.error(f"Goldticket transaction not successful: {result}")
                message.edit_text(f"{emo.ERROR} {result}")
                return

            ex_link = f'<a href="{lamden.explorer_url}/transactions/{tx_hash}">View Transaction on Explorer</a>'

            cur_users = len(lamden.get_contract_variable(contract, "user_list")["value"])
            max_users = lamden.get_contract_variable(contract, "max_entries")["value"]

            message.edit_text(
                f"Thanks entering Goldticket - you are entry {cur_users}/{max_users}\n{ex_link}",
                parse_mode=ParseMode.HTML)

            msg = f"{emo.TICKET} Ticket bought"
            context.bot.answer_callback_query(update.callback_query.id, msg)

    def get_buttons(self, user_id):
        menu = utl.build_menu([
            InlineKeyboardButton("Send TAU & GOLD", callback_data=f"{self.name}|{user_id}|SEND"),
            InlineKeyboardButton("Read How-To", callback_data=f"{self.name}|{user_id}|READ")
        ])
        return InlineKeyboardMarkup(menu, resize_keyboard=True)
