import logging
import datetime

from telegram import ParseMode
from telegram.ext import CallbackContext
from tgbf.plugin import TGBFPlugin


class Goldchange(TGBFPlugin):

    def load(self):
        if not self.table_exists("price_change"):
            sql = self.get_resource("create_list.sql")
            self.execute_sql(sql)

        update_interval = self.config.get("update_interval")
        self.run_repeating(self.check_price_change, update_interval)

    def check_price_change(self, context: CallbackContext):
        logging.info("Checking for large price changes...")

        exclusion_list = list()
        excls = self.execute_sql(self.get_resource("select_list.sql"))
        if excls and excls["data"]:
            for excl in excls["data"]:
                exclusion_list.append(excl[0])

        new_list = list()
        days_to_avg = self.config.get("days_to_avg")
        hours_to_avg = "-" + str(days_to_avg * 24) + " hours"
        chg_perc = self.config.get("chg_perc")
        sql = self.get_resource("select_large_trades.sql")
        new_recs = self.execute_sql(sql, hours_to_avg, chg_perc, plugin="trades")

        if new_recs and new_recs["data"]:
            for new_rec in new_recs["data"]:
                new_list.append(new_rec[0])
                if new_rec[0] not in exclusion_list:
                    logging.info(f"New large price change found: {new_rec}")

                    try:
                        if new_rec[3] > 0:
                            pretty_perc = "+" + str(round(new_rec[3])) + "%"
                        else:
                            pretty_perc = str(round(new_rec[3])) + "%"

                        self.bot.updater.bot.send_message(
                            self.config.get("listing_chat_id"),
                            f"<b>LARGE PRICE CHANGE ON ROCKETSWAP</b>\n"
                            f"Based on average price of last {days_to_avg}d\n\n"
                            f"{new_rec[0]}: <code>{pretty_perc}</code>\n"
                            f"<code>Average Price: {float(new_rec[1]):,.8f}</code>\n"
                            f"<code>Current Price: {float(new_rec[2]):,.8f}</code>\n",
                            parse_mode=ParseMode.HTML
                        )
                        self.execute_sql(
                            self.get_resource("insert_list.sql"),
                            new_rec[0],
                            new_rec[1],
                            new_rec[2],
                            new_rec[3],
                            datetime.datetime.now())

                    except Exception as e:
                        self.notify(f"Can't notify about new price change: {e}")

        for ts in exclusion_list:
            if ts not in new_list:
                self.execute_sql(self.get_resource("delete_list.sql"), ts)
