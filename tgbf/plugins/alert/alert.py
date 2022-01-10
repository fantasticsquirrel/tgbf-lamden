import logging
import tgbf.emoji as emo
import tgbf.utils as utl

from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Alert(TGBFPlugin):

    def load(self):
        if not self.table_exists("alerts"):
            sql = self.get_resource("create_alerts.sql")
            self.execute_sql(sql)

        if not self.table_exists("payed"):
            sql = self.get_resource("create_payed.sql")
            self.execute_sql(sql)

        self.add_handler(CommandHandler(
            self.name,
            self.alert_callback,
            run_async=True))

        self.add_handler(CallbackQueryHandler(
            self.button_callback,
            run_async=True))

        update_interval = self.config.get("update_interval")
        self.run_repeating(self.check_alerts, update_interval)

    @TGBFPlugin.private
    @TGBFPlugin.send_typing
    def alert_callback(self, update: Update, context: CallbackContext):
        if len(context.args) == 2:
            token_symbol = context.args[0].upper()

            sql = self.get_resource("select_contract.sql", plugin="tokens")
            token_data = self.execute_sql(sql, token_symbol, plugin="tokens")["data"]

            if not token_data:
                msg = f"{emo.ERROR} Unknown token symbol"
                update.message.reply_text(msg)
                return

            token_price = context.args[1]

            try:
                token_price = float(token_price)
            except:
                msg = f"{emo.ERROR} Price not valid"
                update.message.reply_text(msg)
                return

            user_id = update.effective_user.id

            if user_id not in self.config.get("whitelist"):
                # Check payment
                sql = self.get_resource("select_payed.sql")
                res = self.execute_sql(sql, update.effective_user.id)
                if len(res["data"]) != 1:
                    check_msg = f"{emo.HOURGLASS} Calculating one-time payment..."
                    message = update.message.reply_text(check_msg)

                    lhc_price = Connect().get_contract_variable(
                        self.config.get("rocketswap_contract"),
                        "prices",
                        self.config.get("lhc_contract"))

                    lhc_price = lhc_price["value"] if "value" in lhc_price else 0
                    lhc_price = float(str(lhc_price)) if lhc_price else float("0")

                    lhc_amount = int(self.config.get("tau_price") / lhc_price)

                    message.edit_text(
                        f"Pay <code>{lhc_amount}</code> LHC once to "
                        f"be able to use /alert for a lifetime",
                        parse_mode=ParseMode.HTML,
                        reply_markup=self.get_pay_button(user_id, lhc_amount))

                    return

        elif len(context.args) == 1 and context.args[0].lower() == "list":
            alerts = self.execute_sql(
                self.get_resource("select_alerts.sql"),
                update.effective_user.id)

            if alerts["data"]:
                for alert in alerts["data"]:
                    update.message.reply_text(
                        f"<code>{alert[1]}</code> price at <code>{alert[2]}</code>",
                        reply_markup=self.get_remove_button(update.effective_user.id, alert[0]),
                        parse_mode=ParseMode.HTML)
            else:
                update.message.reply_text(f"{emo.ERROR} No alert found")
            return
        else:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        sql = self.get_resource("select_alerts.sql")
        res = self.execute_sql(sql, update.effective_user.id)
        if len(res["data"]) >= self.config.get("max_alerts_per_user"):
            msg = f"{emo.ERROR} Max amount of alerts reached"
            update.message.reply_text(msg)
            return

        self.execute_sql(
            self.get_resource("insert_alert.sql"),
            update.effective_user.id,
            token_symbol,
            token_price)

        update.message.reply_text(f"{emo.DONE} Alert added")

    def button_callback(self, update: Update, context: CallbackContext):
        data = update.callback_query.data

        if not data.startswith(self.name):
            return

        data_list = data.split("|")

        if not data_list:
            return

        # Remove alert
        if len(data_list) == 3:
            if int(data_list[1]) != update.effective_user.id:
                return

            sql = self.get_resource("delete_alert.sql")
            self.execute_sql(sql, data_list[2])

            context.bot.delete_message(
                update.effective_user.id,
                update.callback_query.message.message_id)

            context.bot.answer_callback_query(update.callback_query.id, "Alert removed")

        # Pay LHC fee
        elif len(data_list) == 4:
            update.callback_query.message.edit_text(f"{emo.HOURGLASS} Paying LHC fee...")

            usr_id = update.effective_user.id
            wallet = self.get_wallet(usr_id)
            lamden = Connect(wallet)

            try:
                # Send LHC
                send = lamden.send(
                    int(data_list[2]),
                    self.config.get("send_lhc_to"),
                    token="con_collider_contract")
            except Exception as e:
                msg = f"Could not send transaction: {e}"
                update.callback_query.message.edit_text(f"{emo.ERROR} {e}")
                logging.error(msg)
                return

            if "error" in send:
                msg = f"Transaction replied error: {send['error']}"
                update.callback_query.message.edit_text(f"{emo.ERROR} {send['error']}")
                logging.error(msg)
                return

            # Get transaction hash
            tx_hash = send["hash"]

            logging.info(f"Sent {data_list[2]} LHC from {wallet.verifying_key} "
                         f"to {self.config.get('send_lhc_to')}: {send}")

            # Wait for transaction to be completed
            success, result = lamden.tx_succeeded(tx_hash)

            if not success:
                logging.error(f"Transaction not successful: {result}")

                link = f'<a href="{lamden.explorer_url}/transactions/{tx_hash}">TRANSACTION FAILED</a>'

                update.callback_query.message.edit_text(
                    f"{emo.STOP} Could not send <code>{data_list[2]}</code> LHC\n{link}",
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True)
                return
            else:
                if result["result"].startswith("AssertionError"):
                    update.callback_query.message.edit_text(f"{emo.ERROR} {result['result']}")
                else:
                    sql = self.get_resource("insert_payed.sql")
                    self.execute_sql(sql, update.callback_query.from_user.id)

                    update.callback_query.message.edit_text(f"{emo.DONE} You can now use /alert")

    def get_pay_button(self, user_id, amount):
        menu = utl.build_menu([
            InlineKeyboardButton(
                f"Pay {amount} LHC", callback_data=f"{self.name}|{user_id}|{amount}|PAY")
        ])
        return InlineKeyboardMarkup(menu, resize_keyboard=True)

    def get_remove_button(self, user_id, alert_id):
        menu = utl.build_menu([
            InlineKeyboardButton(f"{emo.STOP} Remove alert", callback_data=f"{self.name}|{user_id}|{alert_id}")
        ])
        return InlineKeyboardMarkup(menu, resize_keyboard=True)

    def check_alerts(self, context: CallbackContext):
        if self.plugin_available("trades"):
            alerts = self.execute_sql(self.get_resource("select_all_alerts.sql"))["data"]
            snapshot = self.get_plugin("trades").get_snapshot()

            for alert in alerts:
                if alert[0] in snapshot:
                    alert_price = alert[1]
                    current, previous = snapshot[alert[0]]

                    if not previous:
                        continue

                    current = float(current)
                    previous = float(previous)

                    if previous <= alert_price <= current:
                        self.execute_sql(self.get_resource("delete_alert.sql"), alert[3])
                        context.bot.send_message(alert[2], f"{emo.GREEN} {alert[0]} crossed {alert[1]}")
                        continue

                    if previous >= alert_price >= current:
                        self.execute_sql(self.get_resource("delete_alert.sql"), alert[3])
                        context.bot.send_message(alert[2], f"{emo.RED} {alert[0]} crossed {alert[1]}")
