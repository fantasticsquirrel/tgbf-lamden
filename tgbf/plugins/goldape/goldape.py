import logging
import tgbf.emoji as emo

from telegram import Update, ParseMode
from telegram.ext import CommandHandler, CallbackContext
from tgbf.lamden.connect import Connect
from tgbf.lamden.rocketswap import Rocketswap
from tgbf.plugin import TGBFPlugin


class Goldape(TGBFPlugin):

    def load(self):
        if not self.table_exists("listings"):
            sql = self.get_resource("create_listings.sql")
            self.execute_sql(sql)

        self.add_handler(CommandHandler(
            self.name,
            self.goldape_callback,
            run_async=True))

        update_interval = self.config.get("update_interval")
        self.run_repeating(self.check_tokens, update_interval)

    @TGBFPlugin.private
    @TGBFPlugin.send_typing
    def goldape_callback(self, update: Update, context: CallbackContext):
        # TODO
        pass

    def check_tokens(self, context: CallbackContext):
        contract_list = list()

        listings = self.execute_sql(self.get_resource("select_listings.sql"))

        if listings and listings["data"]:
            for listing in listings["data"][0]:
                contract_list.append(listing)

        rs = Rocketswap()

        for market in rs.get_market_summaries_w_token():
            if market["contract_name"] not in listings:
                logging.info(f"New listing on Rocketswap found: {market}")

                token_info = rs.token(market["contract_name"])
                base_supply = token_info["token"]["base_supply"]

                self.bot.updater.bot.send_message(
                    self.config.get("listing_chat_id"),
                    f"<b>NEW LISTING ON ROCKETSWAP</b>\n\n"
                    f"{market['token_name']}({market['token_symbol']})\n\n"
                    f"Base Supply:\n"
                    f"{base_supply}\n\n"
                    f"Reserves:\n"
                    f"TAU: {market['reserves'][0]}\n"
                    f"{market['token_symbol']}: {market['reserves'][0]}\n\n"
                    f"Current Price:\n"
                    f"{market['Last']}",
                    parse_mode=ParseMode.HTML
                )
