import ast
import logging
import os.path

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
            update.message.reply_photo(
                photo=open(os.path.join(self.get_res_path(), "plant.jpg"), "rb"),
                caption=self.get_resource("plant.md"),
                parse_mode=ParseMode.MARKDOWN)
            return

        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet)

        first_argument = context.args[0].lower()
        contract = self.config.get("contract")

        # ------ SEASON ------
        if first_argument == "season":
            blockservice = self.config.get("blockservice") + f"current/all/{contract}/plants/"

            with requests.get(blockservice) as res:
                response = res.json()

                ed = response[contract]['plants']['growing_season_end_time']['__time__']
                generation = response[contract]['plants']['active_generation']
                reward_pool = response[contract]['plants'][str(generation)]['total_tau']
                if isinstance(reward_pool, dict):
                    reward_pool = reward_pool['__fixed__']

            update.message.reply_text(
                f"<code>Season End: {ed[0]}-{ed[1]}-{ed[2]} at {ed[3]}:{ed[4]}:{ed[5]}</code>\n"
                f"<code>Active Generation: {generation}</code>\n"
                f"<code>Total Reward Pool: {reward_pool}</code>",
                parse_mode=ParseMode.HTML)

        # ------ SCORING ------
        elif first_argument == "scoring":
            update.message.reply_photo(open(os.path.join(self.get_res_path(), "scoring.png"), "rb"))

        # ------ BUY ------
        elif first_argument == "buy":
            if len(context.args) < 2:
                update.message.reply_photo(
                    photo=open(os.path.join(self.get_res_path(), "plant.jpg"), "rb"),
                    caption=self.get_resource("plant.md"),
                    parse_mode=ParseMode.MARKDOWN)
                return

            second_argument = context.args[1].lower()

            if len(context.args) > 2:
                third_argument = context.args[2]
            else:
                third_argument = False

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
                    kwargs={"nick": second_argument, "referrer": third_argument})

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

            update.message.reply_text(
                text=f'<code>Water: {result_list[0]}</code>\n'
                     f'<code>Photosynthesis: {result_list[1]}</code>\n'
                     f'<code>Bugs: {result_list[2]}</code>\n'
                     f'<code>Nutrients: {result_list[3]}</code>\n'
                     f'<code>Weeds: {result_list[4]}</code>\n'
                     f'<code>Toxicity: {result_list[5]}</code>\n'
                     f'<code>Burn amount: {result_list[6]}</code>\n'
                     f'<code>Weather: {result_list[7]}</code>\n\n'
                     f'<code>{result_list[8]}</code>',
                parse_mode=ParseMode.HTML)

        else:
            if len(context.args) > 1:
                second_argument = context.args[1].lower()

                # ------ STATS ------
                if second_argument == "stats":
                    blockservice = self.config.get("blockservice") + f"current/all/{contract}/"

                    with requests.get(blockservice + f"collection_nfts/{first_argument}") as bs:
                        res = bs.json()[contract]['collection_nfts'][first_argument]

                        plant_generation = res["__hash_self__"][0]
                        plant_number = res["__hash_self__"][1]
                        plant_name = f'Gen_{plant_generation}_{plant_number}'

                    with requests.get(blockservice + f"collection_nfts/{plant_name}") as bs:
                        plant_data = bs.json()[contract]['collection_nfts'][plant_name]
                        ipfs_url = plant_data["__hash_self__"]["ipfs_image_url"]

                        meta = bs.json()[contract]['collection_nfts'][plant_name]['nft_metadata']

                        if meta['current_weather'] == 1:
                            weather = "sunny"
                        elif meta['current_weather'] == 2:
                            weather = "cloudy"
                        elif meta['current_weather'] == 3:
                            weather = "rainy"
                        else:
                            weather = meta['current_weather']

                        alve = meta['alive']
                        burn = meta['burn_amount']
                        bugs = meta['current_bugs']
                        nutr = meta['current_nutrients']
                        phto = meta['current_photosynthesis']
                        toxi = meta['current_toxicity']
                        watr = meta['current_water']
                        weed = meta['current_weeds']

                        lc = meta['last_calc']['__time__']
                        ld = meta['last_daily']['__time__']
                        lgl = meta['last_grow_light']['__time__']
                        li = meta['last_interaction']['__time__']
                        lsw = meta['last_squash_weed']['__time__']

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
                             f"<code>Last calculation: {lc[0]}-{lc[1]}-{lc[2]} at {lc[3]}:{lc[4]}:{lc[5]}</code>\n"
                             f"<code>Last daily      : {ld[0]}-{ld[1]}-{ld[2]} at {ld[3]}:{ld[4]}:{ld[5]}</code>\n"
                             f"<code>Last grow light : {lgl[0]}-{lgl[1]}-{lgl[2]} at {lgl[3]}:{lgl[4]}:{lgl[5]}</code>\n"
                             f"<code>Last interaction: {li[0]}-{li[1]}-{li[2]} at {li[3]}:{li[4]}:{li[5]}</code>\n"
                             f"<code>Last squash weed: {lsw[0]}-{lsw[1]}-{lsw[2]} at {lsw[3]}:{lsw[4]}:{lsw[5]}</code>\n\n"
                             f"<code>{ipfs_url}</code>",
                        parse_mode=ParseMode.HTML)

                    
                        # ------ score ------
                elif second_argument == "score":
                    blockservice = self.config.get("blockservice") + f"current/all/{contract}/"

                    with requests.get(blockservice + f"collection_nfts/{first_argument}") as bs:
                        res = bs.json()[contract]['collection_nfts'][first_argument]

                        plant_generation = res["__hash_self__"][0]
                        plant_number = res["__hash_self__"][1]
                        plant_name = f'Gen_{plant_generation}_{plant_number}'

                    with requests.get(blockservice + f"collection_nfts/{plant_name}") as bs:
                        plant_data = bs.json()[contract]['collection_nfts'][plant_name]

                        meta = bs.json()[contract]['collection_nfts'][plant_name]['nft_metadata']
                        burn = meta['burn_amount']
                        toxi = meta['current_toxicity']
                        phto = meta['current_photosynthesis']
                    
                        calc = bs.json()[contract]['collection_nfts'][plant_name]['plant_calc_data']
                        bugs = calc['total_bugs']
                        nutr = calc['total_nutrients']
                        watr = calc['total_water']
                        weed = calc['total_weeds']

                        bonus = bs.json()[contract]['collection_nfts'][plant_name]['bonus_berries']

                        berries = (bonus + (1000 * ((watr*bugs*nutr*weed)/(14**4))*(1-toxi/100)*(phto/100)*(1-burn/100)))

                    update.message.reply_text(
                    f"<code>Current Score: {berries}</code>",
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

                    message = update.message.reply_text(f"{emo.HOURGLASS} Working in the garden...")

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
                        message.edit_text(f"{emo.ERROR} {e}")
                        return

                    if "error" in interact:
                        logging.error(f"nickname_interaction() from {contract} contract returned error: {interact['error']}")
                        message.edit_text(f"{emo.ERROR} {interact['error']}")
                        return

                    tx_hash = interact["hash"]

                    success, result = lamden.tx_succeeded(tx_hash)

                    if not success:
                        logging.error(f"Transaction not successful: {result}")
                        msg = f"{emo.ERROR} {result}"
                        message.edit_text(msg)
                        return

                    # Result is a list with properties
                    if str(result["result"]).startswith("["):
                        result_list = ast.literal_eval(result['result'])

                        if result_list[7] == 1:
                            weather = "sunny"
                        elif result_list[7] == 2:
                            weather = "cloudy"
                        elif result_list[7] == 3:
                            weather = "rainy"
                        else:
                            weather = result_list[7]

                        message.edit_text(
                            text=f'<code>Water: {result_list[0]}</code>\n'
                                 f'<code>Photosynthesis: {result_list[1]}</code>\n'
                                 f'<code>Bugs: {result_list[2]}</code>\n'
                                 f'<code>Nutrients: {result_list[3]}</code>\n'
                                 f'<code>Weeds: {result_list[4]}</code>\n'
                                 f'<code>Toxicity: {result_list[5]}</code>\n'
                                 f'<code>Burn amount: {result_list[6]}</code>\n'
                                 f'<code>Weather: {weather}</code>',
                            parse_mode=ParseMode.HTML)

                    # Result is a string (means plant is dead)
                    else:
                        message.edit_text(
                            text=f'{result["result"]}',
                            parse_mode=ParseMode.HTML)

            # ------ EVERYTHING ELSE ------
            else:
                update.message.reply_photo(
                    photo=open(os.path.join(self.get_res_path(), "plant.jpg"), "rb"),
                    caption=self.get_resource("plant.md"),
                    parse_mode=ParseMode.MARKDOWN)
                return
