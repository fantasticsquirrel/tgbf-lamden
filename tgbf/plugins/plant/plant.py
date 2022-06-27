import ast
import logging
import os.path

import requests
import urllib.request
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
            update.message.reply_photo(
                photo=open(os.path.join(self.get_res_path(), "plant.png"), "rb"),
                caption=self.get_resource("plant.md"),
                parse_mode=ParseMode.MARKDOWN)
            return

        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet)

        first_argument = context.args[0].lower()
        contract = self.config.get("contract")

        # ------ 1 ARGUMENT ------
        if len(context.args) == 1:

            # ------ SEASON ------
            if first_argument == "season":
                blockservice = self.config.get("blockservice") + f"current/all/{contract}/plants/"
                bs_season_end = blockservice + "growing_season_end_time"
                bs_active_gen = blockservice + "active_generation"

                with requests.get(bs_season_end) as season_end:
                    season_end_json = season_end.json()
                    ed = season_end_json[contract]['plants']['growing_season_end_time']['__time__']

                with requests.get(bs_active_gen) as active_gen:
                    active_gen_json = active_gen.json()
                    generation = active_gen_json[contract]['plants']['active_generation']

                update.message.reply_text(
                    f"<code>Season End: {ed[0]}-{ed[1]}-{ed[2]} at {ed[3]}:{ed[4]}:{ed[5]}</code>\n"
                    f"<code>Active Generation: {generation}</code>",
                    parse_mode=ParseMode.HTML)

            # ------ EVERYTHING ELSE ------
            else:
                update.message.reply_photo(
                    photo=open(os.path.join(self.get_res_path(), "plant.png"), "rb"),
                    caption=self.get_resource("plant.md"),
                    parse_mode=ParseMode.MARKDOWN)
                return

        # ------ 2 ARGUMENTS ------
        if len(context.args) == 2:
            second_argument = context.args[1].lower()

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
                        kwargs={"nick": second_argument})

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

                result_list = ast.literal_eval(result['result'])
                result_ipfs = result_list[-1]

                #filename = result_ipfs.split("=")[-1]
                #img_path = os.path.join(self.get_res_path(), filename)

                ex_url = f"{lamden.explorer_url}/transactions/{tx_hash}"

                #urllib.request.urlretrieve(result_ipfs, img_path)

                update.message.reply_text(
                    text=f'<code>Water: {result_list[0]}</code>\n'
                         f'<code>Photosynthesis: {result_list[1]}</code>\n'
                         f'<code>Bugs: {result_list[2]}</code>\n'
                         f'<code>Nutrients: {result_list[3]}</code>\n'
                         f'<code>Weed: {result_list[4]}</code>\n'
                         f'<code>Toxicity: {result_list[5]}</code>\n'
                         f'<code>Burn amount: {result_list[6]}</code>\n'
                         f'<code>Weather: {result_list[7]}</code>\n\n'
                         f'<code>{result_list[8]}</code>',
                    parse_mode=ParseMode.HTML)

            # ------ STATS ------
            elif first_argument == "stats":
                blockservice = self.config.get("blockservice") + f"current/all/{contract}/"

                with requests.get(blockservice + f"collection_nfts/{second_argument}") as bs:
                    res = bs.json()[contract]['collection_nfts'][second_argument]

                    plant_generation = res[0]
                    plant_number = res[1]
                    plant_name = f'Gen_{plant_generation}_{plant_number}'

                with requests.get(blockservice + f"collection_nfts/{plant_name}:nft_metadata") as bs:
                    res = bs.json()[contract]['collection_nfts'][plant_name]['nft_metadata']

                    if res['current_weather'] == 1:
                        weather = "sunny"
                    elif res['current_weather'] == 2:
                        weather = "cloudy"
                    elif res['current_weather'] == 3:
                        weather = "rainy"
                    else:
                        weather = res['current_weather']

                    alve = res['alive']
                    burn = res['burn_amount']
                    bugs = res['current_bugs']
                    nutr = res['current_nutrients']
                    phto = res['current_photosynthesis']
                    toxi = res['current_toxicity']
                    watr = res['current_water']
                    weed = res['current_weeds']

                    last_calc = res['last_calc']['__time__']
                    ld = res['last_daily']['__time__']
                    lgl = res['last_grow_light']['__time__']
                    li = res['last_interaction']['__time__']
                    lsw = res['last_squash_weed']['__time__']

                update.message.reply_text(
                    text=f"<code>Alive: {alve}</code>\n"
                         f"<code>Burn amount: {burn}</code>\n"
                         f"<code>Bugs: {bugs}</code>\n"
                         f"<code>Nutrients: {nutr}</code>\n"
                         f"<code>Photosynthesis: {phto}</code>\n"
                         f"<code>Toxicity: {toxi}</code>\n"
                         f"<code>Water: {watr}</code>\n"
                         f"<code>Weather: {weather}</code>\n"
                         f"<code>Weeds: {weed}</code>\n\n"
                         f"<code>Last calculation: {ld[0]}-{ld[1]}-{ld[2]} at {ld[3]}:{ld[4]}:{ld[5]}</code>\n"
                         f"<code>Last daily      : {ld[0]}-{ld[1]}-{ld[2]} at {ld[3]}:{ld[4]}:{ld[5]}</code>\n"
                         f"<code>Last grow light : {lgl[0]}-{lgl[1]}-{lgl[2]} at {lgl[3]}:{lgl[4]}:{lgl[5]}</code>\n"
                         f"<code>Last interaction: {li[0]}-{li[1]}-{li[2]} at {li[3]}:{li[4]}:{li[5]}</code>\n"
                         f"<code>Last squash weed: {lsw[0]}-{lsw[1]}-{lsw[2]} at {lsw[3]}:{lsw[4]}:{lsw[5]}</code>\n",
                    parse_mode=ParseMode.HTML)

            # ------ INTERACT WITH PLANT BY NAME ------
            else:

                action_types = [
                    "water",
                    "squash",
                    "spraybugs",
                    "growlights",
                    "shade",
                    "fertilize",
                    "pullweeds",
                    "sprayweeds",
                    "finalize",
                    "sellberries"
                ]

                if second_argument not in action_types:
                    update.message.reply_text(
                        f'{emo.ERROR} you can only use following actions: {", ".join(action_types)}',
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True)
                    return

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
