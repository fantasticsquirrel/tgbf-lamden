import io
import json
import plotly
import pandas as pd
import plotly.io as pio
import plotly.graph_objs as go
import tgbf.utils as utl
import tgbf.emoji as emo

from io import BytesIO
from pandas import DataFrame
from telegram import ParseMode, Update
from telegram.ext import CommandHandler, CallbackContext
from pycoingecko import CoinGeckoAPI
from tgbf.plugin import TGBFPlugin


class Chart(TGBFPlugin):

    # CoinGecko ID
    CGID = "lamden"

    def load(self):
        plotly.io.orca.ensure_server()

        self.add_handler(CommandHandler(
            self.name,
            self.chart_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def chart_callback(self, update: Update, context: CallbackContext):
        base = "btc"  # vs-currency
        time = 3      # days

        if context.args:
            if len(context.args) > 2:
                update.message.reply_text(
                    self.get_usage(),
                    parse_mode=ParseMode.MARKDOWN_V2)
                return
            if context.args[0].lower() == "usage":
                update.message.reply_text(
                    self.get_usage(),
                    parse_mode=ParseMode.MARKDOWN_V2)
                return

            if len(context.args) == 2:
                # Check if second argument is positive integer (timeframe in days)
                try:
                    if int(context.args[1]) < 1:
                        raise ValueError()
                except:
                    update.message.reply_text(
                        f"{emo.ERROR} First argument needs to be ticker symbol and "
                        f"second argument needs to be positive whole number (days)")
                    return

                base = context.args[0].lower()
                time = int(context.args[1])

            elif len(context.args) == 1:
                # Check if argument is a number
                if utl.is_numeric(context.args[0]):
                    # Check if argument is positive integer (timeframe in days)
                    try:
                        if int(context.args[0]) < 1:
                            raise ValueError()

                        time = context.args[0]
                    except:
                        update.message.reply_text(
                            f"{emo.ERROR} Argument needs to be "
                            f"positive whole number (days)")
                        return
                else:
                    base = context.args[0].lower()

        try:
            info = CoinGeckoAPI().get_coin_by_id(self.CGID)
            market = CoinGeckoAPI().get_coin_market_chart_by_id(self.CGID, base, time)
        except Exception as e:
            try:
                error = json.loads(str(e).replace("'", '"'))
                if "error" in error:
                    error = error["error"]
                raise ValueError(error)
            except Exception as e:
                update.message.reply_text(f"{emo.ERROR} {str(e).capitalize()}")
                return

        # Volume
        df_volume = DataFrame(market["total_volumes"], columns=["DateTime", "Volume"])
        df_volume["DateTime"] = pd.to_datetime(df_volume["DateTime"], unit="ms")
        volume = go.Scatter(
            x=df_volume.get("DateTime"),
            y=df_volume.get("Volume"),
            name="Volume"
        )

        # Price
        df_price = DataFrame(market["prices"], columns=["DateTime", "Price"])
        df_price["DateTime"] = pd.to_datetime(df_price["DateTime"], unit="ms")
        price = go.Scatter(
            x=df_price.get("DateTime"),
            y=df_price.get("Price"),
            yaxis="y2",
            name="Price",
            line=dict(
                color="rgb(22, 96, 167)",
                width=2
            )
        )

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

        layout = go.Layout(
            images=[dict(
                source=info["image"]["large"],
                opacity=0.8,
                xref="paper", yref="paper",
                x=1.05, y=1,
                sizex=0.2, sizey=0.2,
                xanchor="right", yanchor="bottom"
            )],
            paper_bgcolor='rgb(233,233,233)',
            plot_bgcolor='rgb(233,233,233)',
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
            xaxis=dict(
                gridcolor="rgb(215, 215, 215)"
            ),
            yaxis=dict(
                domain=[0, 0.20],
                gridcolor="rgb(215, 215, 215)",
                zerolinecolor="rgb(233, 233, 233)"
            ),
            yaxis2=dict(
                domain=[0.25, 1],
                gridcolor="rgb(215, 215, 215)",
                zerolinecolor="rgb(233, 233, 233)",
                tickprefix="",
                ticksuffix=""
            ),
            title=dict(
                text=f"{info['symbol'].upper()}/{base.upper()}",
                x=0.5,
                font=dict(
                    size=24
                )
            ),
            legend=dict(
                orientation="h",
                yanchor="top",
                xanchor="center",
                y=1.05,
                x=0.445
            ),
            shapes=[{
                "type": "line",
                "xref": "paper",
                "yref": "y2",
                "x0": 0,
                "x1": 1,
                "y0": market["prices"][len(market["prices"]) - 1][1],
                "y1": market["prices"][len(market["prices"]) - 1][1],
                "line": {
                    "color": "rgb(50, 171, 96)",
                    "width": 1,
                    "dash": "dot"
                }
            }],
        )

        try:
            fig = go.Figure(data=[price, volume], layout=layout)
        except Exception as e:
            return self.notify(e)

        fig["layout"]["yaxis2"].update(tickformat=tickformat)

        update.message.reply_photo(
            photo=io.BufferedReader(BytesIO(pio.to_image(fig, format="png"))),
            quote=False)
