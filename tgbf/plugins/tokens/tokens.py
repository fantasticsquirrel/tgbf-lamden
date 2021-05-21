import logging

from telegram.ext import CallbackContext
from tgbf.plugin import TGBFPlugin
from tgbf.lamden.rocketswap import Rocketswap


class Tokens(TGBFPlugin):

    def load(self):
        if not self.table_exists("tokens"):
            sql = self.get_resource("create_tokens.sql")
            self.execute_sql(sql)

        update_interval = self.config.get("update_interval")
        self.run_repeating(self.update_tokens, update_interval)

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
                    token["token_symbol"],
                    token["token_base64_png"],
                    token["token_base64_svg"]
                )

                logging.info(f"NEW TOKEN: {token}")
