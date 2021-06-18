import time
import logging
import tgbf.emoji as emo
import tgbf.utils as utl

from threading import Thread
from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin
from tgbf.lamden.rocketswap import Rocketswap


class Goldconvert(TGBFPlugin):

    RS_CONTRACT = "con_rocketswap_official_v1_1"
    GOLD_CONTRACT = "con_gold_contract"
    TOKEN_SYMBOL = "GOLD"

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.goldconvert_callback,
            run_async=True))

        self.add_handler(CallbackQueryHandler(
            self.button_callback,
            run_async=True))

    @TGBFPlugin.private
    @TGBFPlugin.send_typing
    def goldconvert_callback(self, update: Update, context: CallbackContext):
        message = update.message.reply_text(
            f"{emo.HOURGLASS} Calculating which tokens could be sold. "
            f"This can take a while..."
        )

        wallet = self.get_wallet(update.effective_user.id)
        balances = Rocketswap().balances(wallet.verifying_key)

        sql = self.get_resource("select_symbol.sql", plugin="tokens")

        threshold = self.config.get("tau_threshold")

        lamden = Connect()

        sell_list = list()
        for contract, balance in balances["balances"].items():
            if contract in ("currency", "con_gold_contract"):
                continue

            symbol = self.execute_sql(sql, contract, plugin="tokens")

            if symbol and symbol["data"]:
                price = lamden.get_contract_variable(
                    "con_rocketswap_official_v1_1",
                    "prices",
                    contract)

                price = price["value"]

                if not price:
                    continue

                if isinstance(price, dict):
                    if "__fixed__" in price:
                        price = price["__fixed__"]

                tau_value = float(price) * float(balance)

                if not tau_value:
                    continue
                if tau_value < threshold:
                    continue
                if balance == 0:
                    continue

                liquidity = lamden.get_contract_variable(
                    "con_rocketswap_official_v1_1",
                    "reserves",
                    contract)

                liquidity = liquidity["value"]

                if not liquidity:
                    continue
                if liquidity[0] <= tau_value:
                    continue

                sell_list.append([symbol["data"][0][0], contract, balance, tau_value])
            else:
                logging.info(f"Unknown token with contract '{contract}'")

        # Sort sell-list
        sell_list.sort(key=lambda x: x[0])

        if not sell_list:
            msg = f"{emo.INFO} No token found that is worth at least {threshold} TAU"
            message.edit_text(msg)
            return

        # Find longest token symbol
        max_length = max([len(sublist[0]) for sublist in sell_list])

        msg = str()
        for entry in sell_list:
            b = float(entry[2])
            b = f"{int(b):,}" if b.is_integer() else f"{b:,.2f}"

            symbol = f"{entry[0]}:"
            msg += f"{symbol:<{max_length + 1}} {b}\n"

        context.user_data["sell_list"] = sell_list

        message.edit_text(
            text=f"<code>{msg}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=self.button_confirm("Convert all to GOLD")
        )

    def button_callback(self, update: Update, context: CallbackContext):
        data = update.callback_query.data

        if not data.startswith(self.name):
            return

        if "sell_list" not in context.user_data:
            msg = f"{emo.WARNING} Message expired"
            context.bot.answer_callback_query(update.callback_query.id, msg)
            return

        sell_list = context.user_data["sell_list"]

        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet)

        message = update.callback_query.message
        message.edit_text(f"{emo.HOURGLASS} Selling assets...")

        threads = [None] * len(sell_list)
        results = [None] * len(sell_list)

        for i in range(len(sell_list)):
            threads[i] = Thread(target=self.sell_asset, args=(lamden, sell_list[i], results, i))
            threads[i].start()
            threads[i].join()

            # Make sure that transactions are processed in order
            time.sleep(0.1)

        message.edit_text(f"{emo.HOURGLASS} Converting to GOLD...")

        total_tau = 0
        for res in results:
            if res:
                try:
                    res = float(res)
                except:
                    res = 0
            else:
                res = 0
            total_tau += res

        try:
            # Check if Rocketswap contract is approved to spend TAU
            approved = lamden.get_approved_amount(self.RS_CONTRACT)
            approved = approved["value"] if "value" in approved else 0
            approved = approved if approved is not None else 0

            msg = f"Approved amount of TAU for {self.RS_CONTRACT}: {approved}"
            logging.info(msg)

            if total_tau > float(approved):
                app = lamden.approve_contract(self.RS_CONTRACT)
                msg = f"Approved {self.RS_CONTRACT} for TAU: {app}"
                logging.info(msg)
        except Exception as e:
            logging.error(f"Error approving {self.RS_CONTRACT} for TAU: {e}")
            message.edit_text(f"{emo.ERROR} {e}")
            return

        # TODO: Remove. Temporal fix
        total_tau = int(total_tau)

        if not total_tau or total_tau <= 0:
            msg = f"{emo.ERROR} Tokens couldn't be sold"
            message.edit_text(msg)
            return

        gold_price = lamden.get_contract_variable("con_rocketswap_official_v1_1", "prices", self.GOLD_CONTRACT)
        gold_price = float(gold_price["value"])

        gold_amount_to_buy = total_tau / gold_price
        min_gold = gold_amount_to_buy / 100 * (100 - self.config.get("slippage"))

        # TODO: Remove. Temporal fix
        min_gold = int(min_gold)

        kwargs = {
            "contract": self.GOLD_CONTRACT,
            "currency_amount": total_tau,
            "minimum_received": min_gold,
            "token_fees": False
        }

        try:
            # Call contract to BUY GOLD
            buy = lamden.post_transaction(
                stamps=150,
                contract=self.RS_CONTRACT,
                function="buy",
                kwargs=kwargs
            )
        except Exception as e:
            logging.error(f"Error calling Rocketswap contract: {e}")
            message.edit_text(f"{emo.ERROR} {e}")
            return

        logging.info(f"Executed Rocketswap - buy contract: {buy}")

        if "error" in buy:
            logging.error(f"Rocketswap - buy contract returned error: {buy['error']}")
            message.edit_text(f"{emo.ERROR} {buy['error']}")
            return

        # Get transaction hash
        tx_hash = buy["hash"]
        logging.info(f"Buying gold tx hash {tx_hash}")

        # Wait for transaction to be completed
        success, result = lamden.tx_succeeded(tx_hash)

        if not success:
            logging.error(f"Transaction not successful: {result}")
            msg = f"{emo.ERROR} Buying GOLD not successful: {result}"
            message.edit_text(msg)
            return

        msg = f"{emo.DONE} Tokens converted to GOLD"
        message.edit_text(msg)

    def button_confirm(self, label: str):
        menu = utl.build_menu([InlineKeyboardButton(label, callback_data=self.name)])
        return InlineKeyboardMarkup(menu, resize_keyboard=True)

    def sell_asset(self, lamden: Connect, token_data: list, results: list, i: int):
        try:
            # Check if contract is approved to spend the token
            approved = lamden.get_approved_amount(self.RS_CONTRACT, token=token_data[1])
            approved = approved["value"] if "value" in approved else 0
            approved = approved if approved is not None else 0

            msg = f"Approved amount of {token_data[0]} for {self.RS_CONTRACT}: {approved}"
            logging.info(msg)

            if float(token_data[2]) > float(approved):
                app = lamden.approve_contract(self.RS_CONTRACT, token=token_data[1])
                msg = f"Approved {self.RS_CONTRACT} for {token_data[1]}: {app}"
                logging.info(msg)
        except Exception as e:
            logging.error(f"Error approving {self.RS_CONTRACT} for {token_data[1]}: {e}")
            results[i] = 0
            return

        token_amount = float(token_data[2])

        # TODO: Remove. Temporal fix
        token_amount = int(token_amount)

        token_price = float(token_data[3])

        min_total = token_price / 100 * (100 - self.config.get("slippage"))

        # TODO: Remove. Temporal fix
        min_total = int(min_total)

        kwargs = {
            "contract": token_data[1],
            "token_amount": token_amount,
            "minimum_received": min_total,
            "token_fees": False
        }

        try:
            # Call contract to SELL token
            sell = lamden.post_transaction(
                stamps=150,
                contract=self.RS_CONTRACT,
                function="sell",
                kwargs=kwargs
            )
        except Exception as e:
            logging.error(f"Error calling Rocketswap contract to sell {token_data[0]}: {e}")
            results[i] = 0
            return

        logging.info(f"Executed Rocketswap - sell {token_data[0]}: {sell}")

        if "error" in sell:
            logging.error(f"Rocketswap - sell {token_data[0]} - contract returned error: {sell['error']}")
            results[i] = 0
            return

        # Get transaction hash
        tx_hash = sell["hash"]
        logging.info(f"{token_data} - {tx_hash}")

        # Wait for transaction to be completed
        success, result = lamden.tx_succeeded(tx_hash)

        if not success:
            logging.error(f"Transaction to sell {token_data[0]} not successful: {result}")
            results[i] = 0
        else:
            if result["result"].startswith("AssertionError"):
                results[i] = 0
            else:
                tau_amount = result["result"][result["result"].find("'")+1:result["result"].rfind("'")]
                results[i] = float(tau_amount) / 100 * self.config.get("tau_for_gold")
