import io
import logging
import datetime
import pandas as pd
import plotly.io as pio
import plotly.graph_objs as go

from telegram import ParseMode
from telegram.ext import CallbackContext
from tgbf.plugin import TGBFPlugin
from pandas import DataFrame
from io import BytesIO


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
        sql = self.get_resource("select_list.sql")
        excls = self.execute_sql(sql)
        if excls and excls["data"]:
            for excl in excls["data"]:
                exclusion_list.append(excl[0])

        logging.info("Getting last trades for each token...")
        sql = self.get_resource("select_last_trades.sql")
        try:
            maxtrades = self.execute_sql(sql, plugin="trades")
        except Exception as e:
            logging.info(f"GoldChange exception attempting to query last trades: {e}")
            return
        if not maxtrades or not maxtrades["data"]:
            logging.info("GoldChange did not find any last trades? Exiting...")
            return

        sql = self.get_resource("select_trades_by_date.sql")
        days_to_avg = self.config.get("days_to_avg")
        hours_to_avg = "-" + str(days_to_avg * 24) + " hours"
        logging.info("Getting trades for each token since " + hours_to_avg + "...")
        try:
            trades = self.execute_sql(sql, hours_to_avg, plugin="trades")
        except Exception as e:
            logging.info(f"GoldChange exception attempting to query trades: {e}")
            return
        if not trades or not trades["data"]:
            logging.info("GoldChange did not find any trades? Exiting...")
            return

        token_working = ""
        token_last_trade = 0
        token_last_price = 0
        tot_amt = 0
        tot_rec = 0

        for rec_token in maxtrades["data"]:
            # logging.info(f"Working: {rec_token}")
            token_working = rec_token[0]
            token_last_price = rec_token[1]
            token_last_trade = rec_token[2]
            tot_amt = 0
            tot_rec = 0
            curr_dict = dict()
            for rec_trade in trades["data"]:
                if rec_trade[0] == token_working:
                    if curr_dict and curr_dict["data"]:
                        curr_dict["data"] += [(
                            rec_trade[2],
                            rec_trade[1]
                        )]
                    else:
                        curr_dict = {"data": [(
                            rec_trade[2],
                            rec_trade[1]
                        )]}
                    if rec_trade[2] != token_last_trade:
                        tot_amt += rec_trade[1]
                        tot_rec += 1
            if tot_rec != 0:
                avg_price = (tot_amt / tot_rec)
                chg_perc = self.config.get("chg_perc")
                price_chg = round(round((1 - (avg_price / token_last_price)), 2) * 100)
                # logging.info(f"Token: {token_working} Avg Price: {float(avg_price)} "
                #             f"Last Price: {float(token_last_price)} Price Change: {price_chg}")
                if abs(price_chg) >= chg_perc:
                    if token_working not in exclusion_list:
                        logging.info(f"New large price change found! {token_working} "
                                     f"Avg Price: {float(avg_price)} "
                                     f"Last Price: {float(token_last_price)} "
                                     f"Price Change: {price_chg}")
                        try:
                            if price_chg > 0:
                                pretty_perc = "+" + str(price_chg) + "%"
                            else:
                                pretty_perc = str(price_chg) + "%"
                            self.bot.updater.bot.send_message(
                                self.config.get("listing_chat_id"),
                                f"<b>LARGE PRICE CHANGE ON ROCKETSWAP</b>\n"
                                f"Based on average price of last {days_to_avg}d\n\n"
                                f"{token_working}: <code>{pretty_perc}</code>\n"
                                f"<code>Average Price: {float(avg_price):,.8f}</code>\n"
                                f"<code>Current Price: {float(token_last_price):,.8f}</code>\n",
                                parse_mode=ParseMode.HTML
                            )
                            sql = self.get_resource("insert_list.sql")
                            self.execute_sql(
                                sql,
                                token_working,
                                avg_price,
                                token_last_price,
                                price_chg,
                                datetime.datetime.now())
                        except Exception as e:
                            self.notify(f"Can't notify about new price change: {e}")

                        # Chart from rschart:
                        df_price = DataFrame(curr_dict["data"], columns=["DateTime", "Price"])
                        df_price["DateTime"] = pd.to_datetime(df_price["DateTime"], unit="s")
                        price = go.Scatter(x=df_price.get("DateTime"), y=df_price.get("Price"))

                        layout = go.Layout(
                            title=dict(
                                text=f"{token_working}-TAU",
                                x=0.5,
                                font=dict(
                                    size=24
                                )
                            ),
                            paper_bgcolor='rgb(233,233,233)',
                            plot_bgcolor='rgb(233,233,233)',
                            xaxis=dict(
                                gridcolor="rgb(215, 215, 215)"
                            ),
                            yaxis=dict(
                                gridcolor="rgb(215, 215, 215)",
                                zerolinecolor="rgb(233, 233, 233)",
                                tickprefix="",
                                ticksuffix=" "
                            ),
                            shapes=[{
                                "type": "line",
                                "xref": "paper",
                                "yref": "y",
                                "x0": 0,
                                "x1": 1,
                                "y0": curr_dict["data"][0][1],
                                "y1": curr_dict["data"][0][1],
                                "line": {
                                    "color": "rgb(50, 171, 96)",
                                    "width": 1,
                                    "dash": "dot"
                                }
                            }]
                        )

                        try:
                            fig = go.Figure(data=[price], layout=layout)
                        except Exception as e:
                            logging.error(e)
                            self.notify(e)
                            return

                        self.bot.updater.bot.sendPhoto(
                            self.config.get("listing_chat_id"),
                            photo=io.BufferedReader(BytesIO(pio.to_image(fig, format="png"))))
                    # else:
                    #    logging.info(f"{token_working} in exclusion list... skipping...")
                else:
                    if token_working in exclusion_list:
                        logging.info(f"{token_working} in exclusion list... removing...")
                        sql = self.get_resource("delete_list.sql")
                        self.execute_sql(sql, token_working)
            # else:
            #     logging.info(token_working + " has no records. Skipping.")
