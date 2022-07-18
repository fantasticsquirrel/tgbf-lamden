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
from os.path import join, isfile
from PIL import Image, ImageFile
from telegram import ParseMode, Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from tgbf.plugin import TGBFPlugin


class Rschart(TGBFPlugin):

    LOGO_DIR = "logos"
    DEF_LOGO = "NO_LOGO.png"

    ImageFile.LOAD_TRUNCATED_IMAGES = True

    def load(self):
        plotly.io.orca.ensure_server()

        self.add_handler(CommandHandler(
            self.handle,
            self.rschart_callback,
            run_async=True))

        self.add_handler(CommandHandler(
            "rc",
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

        result = self.get_chart(token, timeframe)

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

        if len(data_list) < 3:
            return

        token = data_list[1]
        timeframe = data_list[2]

        result = self.get_chart(token, float(timeframe))

        if not result["success"]:
            update.callback_query.message.reply_text(result["data"])
            return

        try:
            update.callback_query.message.edit_media(
                media=InputMediaPhoto(
                    media=io.BufferedReader(BytesIO(pio.to_image(result['data'], format="png")))),
                reply_markup=self.get_button(token, timeframe))

            msg = f"Chart updated"
            context.bot.answer_callback_query(update.callback_query.id, msg)
        except Exception as e:
            error_str = f"{e}"

            if error_str.startswith("Message is not modified"):
                msg = f"No change"
                context.bot.answer_callback_query(update.callback_query.id, msg)

    def get_button(self, token, timeframe):
        menu = utl.build_menu([
            InlineKeyboardButton("Update Chart", callback_data=f"{self.name}|{token}|{timeframe}")
        ])
        return InlineKeyboardMarkup(menu, resize_keyboard=True)

    def get_chart(self, token, timeframe):
        original = token

        if token == "TAU":
            token = "LUSD"

        result = {"success": True, "data": None}

        end_secs = int(time.time() - (timeframe * 24 * 60 * 60))

        sql = self.get_resource("select_trades.sql", plugin="trades")
        res = self.execute_sql(sql, token, end_secs, plugin="trades")

        if not res["data"]:
            msg = f"{emo.ERROR} No trades found"
            result["success"] = False
            result["data"] = msg
            return result

        if original == "TAU":
            for i in range(len(res["data"])):
                res["data"][i] = (res["data"][i][0], 1 / res["data"][i][1])

        df_price = DataFrame(res["data"], columns=["DateTime", "Price"])
        df_price["DateTime"] = pd.to_datetime(df_price["DateTime"], unit="s")
        price = go.Scatter(x=df_price.get("DateTime"), y=df_price.get("Price"))

        image = None

        if original == "TAU":
            logo_path = join(self.get_res_path(), self.LOGO_DIR, f"{original}.jpg")
        else:
            logo_path = join(self.get_res_path(), self.LOGO_DIR, f"{token}.jpg")

        # Try loading logo
        if isfile(logo_path):
            try:
                image = Image.open(logo_path)
            except Exception as e:
                logging.error(f"{emo.ERROR} Can not load logo for '{token}'")
                logging.error(e)
        else:
            # Retrieve logo in base64
            token_logo = self.execute_sql(
                self.get_resource("select_logo.sql", plugin="tokens"),
                token,
                plugin="tokens")

            # Create and save logo
            if token_logo["data"] and token_logo["data"][0][0]:
                with open(logo_path, "wb") as logo_file:
                    img_data = str.encode(token_logo["data"][0][0])
                    logo_file.write(base64.decodebytes(img_data))

                try:
                    # Load logo
                    image = Image.open(logo_path)
                except Exception as e:
                    logging.error(f"{emo.ERROR} Can not load logo for '{token}'")
                    logging.error(e)

        # Load default logo
        if not image:
            image = Image.open(join(self.get_res_path(), self.LOGO_DIR, self.DEF_LOGO))

        margin_l = 130
        tickformat = "0.8f"

        max_value = df_price["Price"].max()
        if max_value > 0.9:
            if max_value > 999:
                margin_l = 90
                tickformat = "0,.0f"
            else:
                margin_l = 95
                tickformat = "0.2f"

        if original == "TAU":
            label = "TAU-LUSD"
        else:
            label = f"{token}-TAU"

        layout = go.Layout(
            images=[dict(
                source=image,
                opacity=0.8,
                xref="paper", yref="paper",
                x=1.05, y=1,
                sizex=0.2, sizey=0.2,
                xanchor="right", yanchor="bottom"
            )],
            title=dict(
                text=label,
                x=0.5,
                font=dict(
                    size=24
                )
            ),
            autosize=False,
            width=800,
            height=600,
            margin=go.layout.Margin(
                l=margin_l,
                r=50,
                b=85,
                t=100,
                pad=4
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

        try:
            fig = go.Figure(data=[price], layout=layout)
            fig["layout"]["yaxis"].update(tickformat=tickformat)

            result["data"] = fig
            return result
        except Exception as e:
            logging.error(e)
            self.notify(e)

            result["success"] = False
            result["data"] = str(repr(e))
            return result
