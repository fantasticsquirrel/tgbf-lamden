import tgbf.emoji as emo
import tgbf.utils as utl

from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext
from tgbf.plugin import TGBFPlugin


# TODO: Check DB of trades plugin and save last price of all tokens in dict
# TODO: How do we handle . and , in prices
class Alert(TGBFPlugin):

    def load(self):
        if not self.table_exists("alerts"):
            sql = self.get_resource("create_alerts.sql")
            self.execute_sql(sql)

        self.add_handler(CommandHandler(
            self.name,
            self.alert_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def alert_callback(self, update: Update, context: CallbackContext):
        if len(context.args) == 2:
            token = context.args[0].upper()

            sql = self.get_resource("select_token.sql")
            token_data = self.execute_sql(sql, token, plugin="tokens")["data"]

            if not token_data:
                msg = f"{emo.ERROR} Unknown token symbol"
                update.message.reply_text(msg)
                return

            # TODO: Needed?
            token_contract = token_data[0][0]

            price = context.args[1]

            try:
                price = float(price)

                if price <= 0:
                    raise ValueError()
            except:
                msg = f"{emo.ERROR} Price not valid"
                update.message.reply_text(msg)
                return

        elif len(context.args) == 1 and context.args[0].lower() == "list":
            alerts = self.get_resource(
                self.execute_sql("select_alerts.sql"),
                update.effective_user.id)

            for alert in alerts:
                update.message.reply_text(
                    f"{emo.ALERT} when {alert[0][1]} price at {alert[0][2]}",
                    reply_markup=self.get_button(update.effective_user.id, alert[0])
                )
                return
        else:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        self.execute_sql(
            self.get_resource("insert_alert.sql"),
            update.effective_user.id,
            token,
            price)

        update.message.reply_text(f"{emo.DONE} Alert added")

    def button_callback(self, update: Update, context: CallbackContext):
        data = update.callback_query.data

        if not data.startswith(self.name):
            return

        data_list = data.split("|")

        if not data_list:
            return

        if len(data_list) != 3:
            return

        if int(data_list[1]) != update.effective_user.id:
            return

        sql = self.get_resource("delete_alarm.sql")
        self.execute_sql(sql, data_list[2])

    def get_button(self, user_id, alert_id):
        menu = utl.build_menu([
            InlineKeyboardButton(f"{emo.STOP} Remove", callback_data=f"{self.name}|{user_id}|{alert_id}")
        ])
        return InlineKeyboardMarkup(menu, resize_keyboard=True)
