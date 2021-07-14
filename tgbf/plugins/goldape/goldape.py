import logging

from telegram import Update, ParseMode
from telegram.ext import CommandHandler, CallbackContext
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
                        f"Base Supply:\n"
                        f"{int(base_supply):,}\n\n"
                        f"Liquidity Reserves:\n"
                        f"TAU: {float(market['reserves'][0]):,.8f}\n"
                        f"{market['token']['token_symbol']}: {float(market['reserves'][1]):,.8f}\n\n"
                        f"Current Price:\n"
                        f"{float(market['Last']):,.8f} TAU",
                        parse_mode=ParseMode.HTML
                    )

                    self.execute_sql(self.get_resource("insert_listing.sql"), market["contract_name"])
                except Exception as e:
                    self.notify(f"Can't notify about new listing: {e}")
