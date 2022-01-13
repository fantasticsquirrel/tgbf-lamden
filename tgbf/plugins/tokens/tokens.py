import logging

import tgbf.emoji as emo

from telegram import Update
from telegram.ext import CallbackContext, CommandHandler
from tgbf.lamden.rocketswap import Rocketswap
from tgbf.plugin import TGBFPlugin


class Tokens(TGBFPlugin):

    def load(self):
        if not self.table_exists("tokens"):
            sql = self.get_resource("create_tokens.sql")
            self.execute_sql(sql)

        self.add_handler(CommandHandler(
            self.name,
            self.token_callback,
            run_async=True))

        update_interval = self.config.get("update_interval")
        self.run_repeating(self.update_tokens, update_interval)

    @TGBFPlugin.owner
    @TGBFPlugin.private
    @TGBFPlugin.send_typing
    def token_callback(self, update: Update, context: CallbackContext):
        if len(context.args) == 1 and context.args[0].lower() == "refresh":
            for token in Rocketswap().token_list():
                self.execute_sql(
                    self.get_resource("update_token.sql"),
                    token["token_name"],
                    token["token_symbol"].upper(),
                    token["token_base64_png"],
                    token["token_base64_svg"],
                    token["contract_name"])

                logging.info(f"TOKEN REFRESHED: {token}")

            update.message.reply_text(f"{emo.DONE} Tokens refreshed")

    def update_tokens(self, context: CallbackContext):
        res = self.execute_sql(self.get_resource("select_contracts.sql"))

        if res and res["data"]:
            contracts = ["%s" % x for x in res["data"]]
        else:
            contracts = list()

        for token in Rocketswap().token_list():
            if token["contract_name"] not in contracts:
                self.execute_sql(
                    self.get_resource("insert_token.sql"),
                    token["contract_name"],
                    token["token_name"],
                    token["token_symbol"].upper(),
                    token["token_base64_png"],
                    token["token_base64_svg"]
                )

                logging.info(f"NEW TOKEN: {token}")
