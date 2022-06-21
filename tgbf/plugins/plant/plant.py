import json
import logging
import requests
import tgbf.emoji as emo

from telegram import Update, ParseMode
from telegram.ext import CommandHandler, CallbackContext
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Plant(TGBFPlugin):

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.plant_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def plant_callback(self, update: Update, context: CallbackContext):
        if len(context.args) < 1:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet)

        first_argument = context.args[0].lower()
        contract = self.config.get("contract")

        # ------ 1 ARGUMENT ------
        if len(context.args) == 1:

            # ------ BUY ------
            if first_argument == "buy":
                try:
                    approved = lamden.get_approved_amount(contract)
                    approved = approved["value"] if "value" in approved else 0
                    approved = approved if approved is not None else 0

                    msg = f"Approved amount of TAU for {contract}: {approved}"
                    logging.info(msg)

                    if float(approved) < 999999:
                        app = lamden.approve_contract(contract)
                        msg = f"Approved {contract}: {app}"
                        logging.info(msg)

                    buy = lamden.post_transaction(
                        stamps=150,
                        contract=contract,
                        function="buy_plant",
                        kwargs={})

                except Exception as e:
                    logging.error(f"Error calling buy_plant() from {contract} contract: {e}")
                    update.message.reply_text(f"{emo.ERROR} {e}")
                    return

                if "error" in buy:
                    logging.error(f"buy_plant() from {contract} contract returned error: {buy['error']}")
                    update.message.reply_text(f"{emo.ERROR} {buy['error']}")
                    return

                tx_hash = buy["hash"]

                success, result = lamden.tx_succeeded(tx_hash)

                if not success:
                    logging.error(f"Transaction not successful: {result}")
                    msg = f"{emo.ERROR} {result}"
                    update.message.reply_text(msg)
                    return

                result_data = result['result']
                result_dict = json.loads(result_data[0])
                result_ipfs = result_data[1]

                ex_url = f"{lamden.explorer_url}/transactions/{tx_hash}"

                # TODO: Format dict in reply message
                update.message.reply_photo(
                    photo=result_ipfs,
                    caption=f'<code>{result_dict}</code> <a href="{ex_url}">View Tx</a>',
                    parse_mode=ParseMode.HTML)

            # ------ SEASON ------
            elif first_argument == "season":
                blockservice = self.config.get("blockservice") + f"current/all/{contract}/plants/"
                bs_season_end = blockservice + "growing_season_end_time"
                bs_active_gen = blockservice + "active_generation"

                with requests.get(bs_season_end) as season_end:
                    season_end_json = season_end.json()

                with requests.get(bs_active_gen) as active_gen:
                    active_gen_json = active_gen.json()

                # TODO: Format correctly and send as message

                update.message.reply_text(
                    f"Season End: {season_end_json}\n\n"
                    f"Active Generation: {active_gen_json}",
                    parse_mode=ParseMode.HTML)

            # ------ EVERYTHING ELSE ------
            else:
                update.message.reply_text(
                    self.get_usage(),
                    parse_mode=ParseMode.MARKDOWN)
                return

        # ------ 2 ARGUMENTS ------
        if len(context.args) == 2:
            second_argument = context.args[1].lower()

            # ------ STATS ------
            if second_argument == "stats":
                blockservice = self.config.get("blockservice") + f"current/all/{contract}/plants/"

                with requests.get(blockservice) as bs:
                    bs_json = bs.json()

                # TODO: Set real stats
                update.message.reply_text(
                    f'{emo.DONE} Executed!',
                    parse_mode=ParseMode.HTML)

            # ------ INTERACT WITH PLANT BY NAME ------
            else:
                try:
                    interact = lamden.post_transaction(
                        stamps=150,
                        contract=contract,
                        function="nickname_interaction",
                        kwargs={
                            "nickname": first_argument,
                            "function_name": second_argument
                        })

                except Exception as e:
                    logging.error(f"Error calling nickname_interaction() from {contract} contract: {e}")
                    update.message.reply_text(f"{emo.ERROR} {e}")
                    return

                if "error" in interact:
                    logging.error(f"nickname_interaction() from {contract} contract returned error: {interact['error']}")
                    update.message.reply_text(f"{emo.ERROR} {interact['error']}")
                    return

                tx_hash = interact["hash"]

                success, result = lamden.tx_succeeded(tx_hash)

                if not success:
                    logging.error(f"Transaction not successful: {result}")
                    msg = f"{emo.ERROR} {result}"
                    update.message.reply_text(msg)
                    return

                ex_url = f"{lamden.explorer_url}/transactions/{tx_hash}"

                update.message.reply_text(
                    f'{emo.DONE} Executed! <a href="{ex_url}">View Tx</a>',
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True)

        # ------ EVERYTHING ELSE ------
        else:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
