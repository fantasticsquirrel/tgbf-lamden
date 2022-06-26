import logging
import tgbf.emoji as emo

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from telegram import ParseMode
from tgbf.plugin import TGBFPlugin
from tgbf.lamden.rocketswap import Rocketswap


class Balance(TGBFPlugin):

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.balance_callback,
            run_async=True))

        self.add_handler(CommandHandler(
            "b",
            self.balance_callback,
            run_async=True))

    @TGBFPlugin.private
    @TGBFPlugin.send_typing
    def balance_callback(self, update: Update, context: CallbackContext):
        wallet = self.get_wallet(update.effective_user.id)
        balances = Rocketswap().balances(wallet.verifying_key)

        sql = self.get_resource("select_symbol.sql", plugin="tokens")

        tau_balance = list()
        balances_list = list()
        for contract, b in balances["balances"].items():
            if contract == "currency":
                tau_balance.append(["TAU", b])
            else:
                symbol = self.execute_sql(sql, contract, plugin="tokens")

                if symbol and symbol["data"]:
                    balances_list.append([symbol["data"][0][0].upper(), b])
                else:
                    logging.info(f"Unknown token with contract '{contract}'")

        # Sort balance list
        balances_list.sort(key=lambda x: x[0])

        if tau_balance:
            balances_list.insert(0, tau_balance[0])

        decimals = self.config.get("decimals")

        min_limit = "0."
        for i in range(decimals - 1):
            min_limit += "0"

        min_limit = float(min_limit + "1")

        if not balances_list:
            msg = f"{emo.INFO} Your wallet is empty"
            update.message.reply_text(msg)
            return

        # Find longest token symbol
        max_length = max([len(t[0]) for t in balances_list if float(t[1]) > min_limit], default=0)

        msg = str()
        for entry in balances_list:
            b = float(entry[1])

            if b < min_limit:
                continue

            b = f"{int(b):,}" if b.is_integer() else f"{b:,.{decimals}f}"

            # Remove any useless zeros at the end
            if "." in b:
                while b.endswith("0"):
                    b = b[:-1]
                if b.endswith("."):
                    b = b[:-1]

            symbol = f"{entry[0]}:"
            msg += f"{symbol:<{max_length + 1}} {b}\n"

        if not msg:
            update.message.reply_text(
                text=f"{emo.INFO} You don't own any tokens")
        else:
            update.message.reply_text(
                text=f"<code>{msg}</code>",
                parse_mode=ParseMode.HTML)
