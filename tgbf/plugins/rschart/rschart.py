import io
import time
import plotly
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

        self.add_handler(CommandHandler(
            self.handle,
            self.rschart_callback,
            run_async=True))

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

        skip = 0
        take = 50
        call = True
        data = list()

        while call:
            try:
                res = requests.get(
                    self.config.get("trade_history_url"),
                    params={"take": take, "skip": skip}
                )
            except Exception as e:
                logging.error(f"Can't retrieve trade history: {e}")
                update.message.reply_text(f"{emo.ERROR} {e}")
                return

            skip += take

            for tx in res.json():
                if tx["token_symbol"] == token_symbol:
                    if int(tx["time"]) > end_secs:
                        data.append([tx["time"], float(tx["price"])])
                    else:
                        call = False
                        break

            if len(res.json()) != take:
                call = False

        if not data:
            msg = f"{emo.ERROR} No data for {token_symbol}"
            update.message.reply_text(msg)
            return

        df_price = DataFrame(reversed(data), columns=["DateTime", "Price"])
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
                "y0": data[0][1],
                "y1": data[0][1],
                "line": {
                    "color": "rgb(50, 171, 96)",
                    "width": 1,
                    "dash": "dot"
                }
            }],
        )

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
