import io
import time
import plotly
import base64
import logging
import pandas as pd
import plotly.io as pio
import plotly.graph_objs as go

import tgbf.emoji as emo
import tgbf.utils as utl

from io import BytesIO
from pandas import DataFrame
from telegram import ParseMode, Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from tgbf.plugin import TGBFPlugin


class Rschart(TGBFPlugin):

    def load(self):
        plotly.io.orca.ensure_server()

        self.add_handler(CommandHandler(
            self.handle,
            self.rschart_callback,
            run_async=True))

        self.add_handler(CallbackQueryHandler(
            self.button_callback,
            run_async=True))

    @TGBFPlugin.blacklist
    @TGBFPlugin.send_typing
    def rschart_callback(self, update: Update, context: CallbackContext):
        if not context.args or len(context.args) > 2:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN_V2)
            return

        token = context.args[0].strip().upper()

        if len(context.args) == 2:
            try:
                timeframe = float(context.args[1])
            except:
                msg = f"{emo.ERROR} Timeframe not valid. Provide number of days"
                update.message.reply_text(msg)
                return
        else:
            timeframe = 3  # days

        result = self.get_image(token, timeframe)

        if not result["success"]:
            update.message.reply_text(result["data"])
            return

        update.message.reply_photo(
            photo=io.BufferedReader(BytesIO(pio.to_image(result['data'], format="png"))),
            reply_markup=self.get_button(token, timeframe))

    def button_callback(self, update: Update, context: CallbackContext):
        data = update.callback_query.data

        if not data.startswith(self.name):
            return

        data_list = data.split("|")

        if not data_list:
            return

        if len(data_list) < 2:
            return

        token = data_list[0]
        timeframe = data_list[1]

        result = self.get_image(token, timeframe)

        if not result["success"]:
            update.callback_query.message.reply_text(result["data"])
            return

        update.callback_query.message.edit_media(
            media=InputMediaPhoto(
                media=io.BufferedReader(BytesIO(pio.to_image(result['data'], format="png")))),
            reply_markup=self.get_button(token, timeframe))

        msg = f"{emo.DONE} Updated"
        context.bot.answer_callback_query(update.callback_query.id, msg)

    def get_button(self, token, timeframe):
        menu = utl.build_menu([
            InlineKeyboardButton("Update Chart", callback_data=f"{token}||{timeframe}")
        ])
        return InlineKeyboardMarkup(menu, resize_keyboard=True)

    def get_image(self, token, timeframe):
        result = {"success": True, "data": None}

        end_secs = int(time.time() - (timeframe * 24 * 60 * 60))

        sql = self.get_resource("select_trades.sql", plugin="trades")
        res = self.execute_sql(sql, token, end_secs, plugin="trades")

        if not res["data"]:
            msg = f"{emo.ERROR} No trades found"
            result["success"] = False
            result["data"] = msg
            return result

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
                text=f"{token}-TAU",
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
            result["data"] = go.Figure(data=[price], layout=layout)
            return result
        except Exception as e:
            logging.error(e)
            self.notify(e)

            result["success"] = False
            result["data"] = str(e)
            return result
