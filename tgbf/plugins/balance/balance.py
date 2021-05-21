import logging

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from telegram import ParseMode
from tgbf.plugin import TGBFPlugin
from tgbf.lamden.rocketswap import Rocketswap


class Balance(TGBFPlugin):

    def load(self):
        if not self.table_exists("tokens"):
            sql = self.get_resource("create_tokens.sql")
            self.execute_sql(sql)

        update_interval = self.config.get("update_interval")
        self.run_repeating(self.update_tokens, update_interval)

        self.add_handler(CommandHandler(
            self.name,
            self.balance_callback,
            run_async=True))

    @TGBFPlugin.private
    @TGBFPlugin.send_typing
    def balance_callback(self, update: Update, context: CallbackContext):
        wallet = self.get_wallet(update.effective_user.id)
        balances = Rocketswap().balances(wallet.verifying_key)

        symbol_sql = self.get_resource("select_symbol.sql")

        tau_balance = list()
        balances_list = list()
        for contract, b in balances["balances"].items():
            if contract == "currency":
                tau_balance.append(["TAU", b])
            else:
                symbol = self.execute_sql(symbol_sql, contract)

                if symbol and symbol["data"]:
                    balances_list.append([symbol["data"][0][0].upper(), b])
                else:
                    logging.info(f"Unknown token with contract '{contract}'")

        # Sort balance list
        balances_list.sort(key=lambda x: x[0])

        if tau_balance:
            balances_list.insert(0, tau_balance[0])

        min_limit = 0.01

        # Find longest token symbol
        max_length = max([len(t[0]) for t in balances_list if float(t[1]) > min_limit])

        msg = str()
        for entry in balances_list:
            b = float(entry[1])

            if b < min_limit:
                continue

            b = f"{int(b):,}" if b.is_integer() else f"{b:,.2f}"

            symbol = f"{entry[0]}:"
            msg += f"{symbol:<{max_length + 1}} {b}\n"

        update.message.reply_text(
            text=f"<code>{msg}</code>",
            parse_mode=ParseMode.HTML
        )

    def update_tokens(self, context: CallbackContext):
        res = self.execute_sql(self.get_resource("select_contracts.sql"))

        if res and res["data"]:
            contracts = ["%s" % x for x in res["data"]]
        else:
            contracts = list()

        for token in Rocketswap().token_list():
            if token["contract_name"] not in contracts:
                self.execute_sql(
                    self.get_resource("insert_token.sql"),
                    token["contract_name"],
                    token["token_name"],
                    token["token_symbol"],
                    token["token_base64_png"],
                    token["token_base64_svg"]
                )

                logging.info(f"NEW TOKEN: {token}")
