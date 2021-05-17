import io
import time
import plotly
import base64
import logging
import pandas as pd
import plotly.io as pio
import plotly.graph_objs as go
import requests

import tgbf.emoji as emo

from io import BytesIO
from pandas import DataFrame
from telegram import ParseMode, Update
from telegram.ext import CommandHandler, CallbackContext
from tgbf.plugin import TGBFPlugin


class Rschart(TGBFPlugin):

    def load(self):
        plotly.io.orca.ensure_server()

        if not self.table_exists("trade_history"):
            sql = self.get_resource("create_trade_history.sql")
            self.execute_sql(sql)

        update_interval = self.config.get("update_interval")
        self.run_repeating(self.update_trades, update_interval)

        self.add_handler(CommandHandler(
            self.handle,
            self.rschart_callback,
            run_async=True))

    def update_trades(self, context: CallbackContext):
        res = self.execute_sql(self.get_resource("select_last_trade.sql"))

        if res and res["data"]:
            last_secs = res["data"][0][0]
        else:
            last_secs = 0

        trades = list()

        skip = 0
        take = 10

        insert_sql = self.get_resource("insert_trade.sql")

        while True:
            try:
                res = requests.get(
                    self.config.get('trade_history_url'),
                    params={"take": take, "skip": skip},
                    timeout=2)
            except Exception as e:
                msg = f"Can't retrieve Rocketswap trade history: {e}"
                logging.error(msg)
                return

            skip += take

            for tx in res.json():
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
                        logging.info(f"New RS trade: {tx}")
                else:
                    return

            if len(res.json()) != take:
                return

    @TGBFPlugin.blacklist
    @TGBFPlugin.send_typing
    def rschart_callback(self, update: Update, context: CallbackContext):
        if not context.args or len(context.args) > 2:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN_V2)
            return

        token_symbol = context.args[0].strip().upper()

        if len(context.args) == 2:
            try:
                timeframe = float(context.args[1])
            except:
                msg = f"{emo.ERROR} Timeframe not valid. Provide number of days"
                update.message.reply_text(msg)
                return
        else:
            timeframe = 3  # days

        end_secs = int(time.time() - (timeframe * 24 * 60 * 60))

        sql = self.get_resource("select_trades.sql")
        res = self.execute_sql(sql, token_symbol, end_secs)

        if not res["data"]:
            msg = f"{emo.ERROR} No trades found"
            update.message.reply_text(msg)
            return

        """
        try:
            res = requests.get(f"{self.config.get('token_url')}/{token_contract}")
        except Exception as e:
            logging.error(f"Can't retrieve trade history: {e}")
            update.message.reply_text(f"{emo.ERROR} {e}")
            return

        if res.json()["token"]["token_base64_png"]:
            img_data = res.json()["token"]["token_base64_png"]
        elif res.json()["token"]["token_base64_svg"]:
            img_data = res.json()["token"]["token_base64_svg"]
        else:
            img_data = None

        image = base64.decodebytes(str.encode(img_data))
        """

        df_price = DataFrame(res["data"], columns=["DateTime", "Price"])
        df_price["DateTime"] = pd.to_datetime(df_price["DateTime"], unit="s")
        price = go.Scatter(x=df_price.get("DateTime"), y=df_price.get("Price"))

        layout = go.Layout(
            title=dict(
                text=f"{token_symbol}-TAU",
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
                "y0": res["data"][0][1],
                "y1": res["data"][0][1],
                "line": {
                    "color": "rgb(50, 171, 96)",
                    "width": 1,
                    "dash": "dot"
                }
            }]
        )

        """
            images=[dict(
                source="set image url",
                opacity=0.8,
                xref="paper", yref="paper",
                x=1.05, y=1,
                sizex=0.2, sizey=0.2,
                xanchor="right", yanchor="bottom"
            )]
        """

        try:
            fig = go.Figure(data=[price], layout=layout)
        except Exception as e:
            update.message.reply_text(str(e))
            logging.error(e)
            self.notify(e)
            return

        update.message.reply_photo(
            photo=io.BufferedReader(BytesIO(pio.to_image(fig, format="png"))),
            quote=False)
