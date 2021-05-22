import logging

from telegram.ext import CallbackContext
from tgbf.plugin import TGBFPlugin
from tgbf.lamden.rocketswap import Rocketswap


class Trades(TGBFPlugin):

    def load(self):
        if not self.table_exists("trades"):
            sql = self.get_resource("create_trades.sql")
            self.execute_sql(sql)

        update_interval = self.config.get("update_interval")
        self.run_repeating(self.update_trades, update_interval)

    def update_trades(self, context: CallbackContext):
        res = self.execute_sql(self.get_resource("select_last_trade.sql"))

        if res and res["data"]:
            last_secs = res["data"][0][0]
        else:
            last_secs = 0

        trades = list()

        skip = 0
        take = 50

        insert_sql = self.get_resource("insert_trade.sql")

        rs = Rocketswap()

        while True:
            res = rs.trade_history(take=take, skip=skip)

            for tx in res:
                if tx["time"] > last_secs:
                    if tx not in trades:
                        trade = [
                            tx["contract_name"],
                            tx["token_symbol"],
                            tx["price"],
                            tx["time"],
                            tx["amount"],
                            tx["type"]
                        ]

                        trades.append(tx)
                        self.execute_sql(insert_sql, *trade)
                        logging.info(f"NEW TRADE: {tx}")
                else:
                    return

            if len(res) != take:
                return

            skip += take
