import io
import logging
import plotly.io as pio
import plotly.graph_objs as go
import tgbf.utils as utl
import tgbf.emoji as emo


from io import BytesIO
from tgbf.plugin import TGBFPlugin
from pytrends.request import TrendReq
from telegram.ext import CommandHandler, CallbackContext
from telegram import Update, ParseMode


# TODO: Make grid gray color
# TODO: Center title
# TODO: Change () to ""
class Trend(TGBFPlugin):

    DEFAULT_T = "today 5-y"

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.trend_callback,
            run_async=True))

    @TGBFPlugin.blacklist
    @TGBFPlugin.send_typing
    def trend_callback(self, update: Update, context: CallbackContext):
        if not context.args:
            update.message.reply_text(
                text=f"{self.get_usage()}",
                parse_mode=ParseMode.MARKDOWN_V2)
            return

        tf = str()
        for arg in context.args:
            if arg.startswith("t="):
                tf = arg.replace("t=", "")
                context.args.remove(arg)
                break

        if tf:
            if tf != "all":
                from datetime import datetime
                now = datetime.today()
                date = utl.get_date(now, tf)

                if not date:
                    msg = f"{emo.ERROR} Timeframe not formatted correctly"
                    update.message.reply_text(msg)
                    return
                else:
                    tf = f"{str(date)[:10]} {str(now)[:10]}"
        else:
            tf = self.DEFAULT_T

        # Check for brackets and combine keywords
        args = self._combine_args(context.args)

        if len(args) > 5:
            msg = f"{emo.ERROR} Not possible to provide more than 5 keywords"
            update.message.reply_text(msg)
            return

        try:
            pytrends = TrendReq(hl='en-US', tz=360)
            pytrends.build_payload(args, cat=0, timeframe=tf, geo='', gprop='')

            data = pytrends.interest_over_time()
        except Exception as e:
            # TODO: Handle error correctly
            logging.error(e)
            return

        no_data = list()
        tr_data = list()
        for kw in args:
            if data.empty:
                no_data = args
                break

            if data.get(kw).empty:
                no_data.append(kw)
                continue

            tr_data.append(go.Scatter(x=data.get(kw).index, y=data.get(kw).values, name=kw))

        if no_data:
            msg = f"{emo.ERROR} No data for keyword(s): {', '.join(no_data)}"
            update.message.reply_text(msg)

        if len(args) == len(no_data):
            return

        layout = go.Layout(
            title="Google Trends - Interest Over Time",
            paper_bgcolor='rgb(233,233,233)',
            plot_bgcolor='rgb(233,233,233)',
            yaxis=dict(
                title="Queries",
                showticklabels=False),
            showlegend=True)

        try:
            fig = go.Figure(data=tr_data, layout=layout)
        except Exception as e:
            # TODO: Handle error correctly
            logging.error(e)
            return

        update.message.reply_photo(io.BufferedReader(BytesIO(pio.to_image(fig, format="png"))))

    def _combine_args(self, args):
        combine = list()
        new_args = list()
        for arg in args:
            if arg.startswith("("):
                combine.append(arg[1:])
                continue
            elif arg.endswith(")"):
                if combine:
                    arg = f"{' '.join(combine)} {arg[:len(arg) - 1]}"
                    combine.clear()
            elif combine:
                combine.append(arg)
                continue
            new_args.append(arg)
        return new_args
