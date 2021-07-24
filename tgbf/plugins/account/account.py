import logging
import tgbf.utils as utl
import tgbf.emoji as emo

from typing import Union
from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from tgbf.lamden.rocketswap import Rocketswap
from tgbf.lamden.connect import Connect
from pycoingecko import CoinGeckoAPI
from tgbf.lamden.api import API
from tgbf.plugin import TGBFPlugin


class Account(TGBFPlugin):

    CGID = "lamden"

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.account_callback,
            run_async=True))

        self.add_handler(CallbackQueryHandler(
            self.button_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def account_callback(self, update: Update, context: CallbackContext):
        if len(context.args) == 1:
            if not API().is_address_valid(context.args[0]):
                msg = f"{emo.ERROR} Address not valid"
                update.message.reply_text(msg)
                return
            else:
                address = context.args[0]
        else:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        cal_msg = f"{emo.HOURGLASS} Checking subscription..."
        message = update.message.reply_text(cal_msg)

        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet)

        deposit = lamden.get_contract_variable(
            self.config.get("lhc_contract"),
            "data",
            wallet.verifying_key
        )

        deposit = deposit["value"] if "value" in deposit else 0
        deposit = float(str(deposit)) if deposit else float("0")

        if deposit > 0 or wallet.verifying_key in self.config.get("whitelist"):
            self.calculate_value(address, message)
        else:
            context.user_data["message"] = message
            context.user_data["address"] = address
            context.user_data["lhc_amount"] = int(self.get_amount_lhc())

            message.edit_text(
                f"Pay <code>{context.user_data['lhc_amount']}</code> LHC "
                f"to see the total value of the provided address",
                reply_markup=self.get_button(update.effective_user.id),
                parse_mode=ParseMode.HTML
            )

    def get_amount_lhc(self):
        lhc_price = Connect().get_contract_variable(
            self.config.get("rocketswap_contract"),
            "prices",
            self.config.get("lhc_contract")
        )

        lhc_price = lhc_price["value"] if "value" in lhc_price else 0
        lhc_price = float(str(lhc_price)) if lhc_price else float("0")

        return self.config.get("tau_amount") / lhc_price

    def get_tau_value(self, contract: str, amount: Union[int, float]):
        price = Connect().get_contract_variable(
            self.config.get("rocketswap_contract"),
            "prices",
            contract
        )

        price = price["value"] if "value" in price else 0
        price = float(str(price)) if price else float("0")

        return int(price * amount)

    def get_button(self, user_id):
        menu = utl.build_menu([
            InlineKeyboardButton("Pay LHC", callback_data=f"{self.name}|{user_id}")
        ])
        return InlineKeyboardMarkup(menu, resize_keyboard=True)

    def button_callback(self, update: Update, context: CallbackContext):
        data = update.callback_query.data
        data_list = data.split("|")

        if not data.startswith(self.name):
            return
        if not data_list:
            return
        if len(data_list) != 2:
            return
        if int(data_list[1]) != update.effective_user.id:
            return

        message = context.user_data["message"]
        address = context.user_data["address"]
        lhc_amount = context.user_data["lhc_amount"]

        message.reply_text(f"{emo.HOURGLASS} Paying LHC fee...")

        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet)

        try:
            # Send LHC
            send = lamden.send(
                lhc_amount,
                self.config.get("send_lhc_to"),
                token="con_collider_contract")
        except Exception as e:
            msg = f"Could not send transaction: {e}"
            message.edit_text(f"{emo.ERROR} {e}")
            logging.error(msg)
            return

        if "error" in send:
            msg = f"Transaction replied error: {send['error']}"
            message.edit_text(f"{emo.ERROR} {send['error']}")
            logging.error(msg)
            return

        # Get transaction hash
        tx_hash = send["hash"]

        logging.info(f"Sent {lhc_amount} LHC from {wallet.verifying_key} "
                     f"to {self.config.get('send_lhc_to')}: {send}")

        # Wait for transaction to be completed
        success, result = lamden.tx_succeeded(tx_hash)

        if not success:
            logging.error(f"Transaction not successful: {result}")

            link = f'<a href="{lamden.explorer_url}/transactions/{tx_hash}">TRANSACTION FAILED</a>'

            message.edit_text(
                f"{emo.STOP} Could not send <code>{lhc_amount}</code> LHC\n{link}",
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True)
            return

        self.calculate_value(address, message)

    def calculate_value(self, address, message):
        message.edit_text(f"{emo.HOURGLASS} Crunching data. This will take a while. Do not "
                          f"trigger the command again. Wait until it's finished.")

        rs = Rocketswap()

        stake_tau = dict()
        lp_tau = dict()
        token_tau = dict()

        msg = str()
        total_tau_value = 0

        # ---- STAKING ----

        staking_meta = rs.staking_meta()

        staked_lp = dict()
        for staking_contract, staking_data in rs.user_staking_info(address).items():
            yield_info = staking_data["yield_info"]

            if not yield_info:
                continue

            user_staked = yield_info["total_staked"]

            if user_staked == 0:
                continue

            if staking_contract.startswith("con_liq_mining_"):
                for staking_meta_data in staking_meta["ents"]:
                    if staking_meta_data["contract_name"] == staking_contract:
                        staked_lp[staking_meta_data["STAKING_TOKEN"]] = user_staked
                        break
            else:
                for staking_meta_data in staking_meta["ents"]:
                    if staking_meta_data["contract_name"] == staking_contract:
                        stake_contract = staking_meta_data["STAKING_TOKEN"]
                        stake_tau[stake_contract] = self.get_tau_value(stake_contract, user_staked)
                        break

                tmp_msg = str()
                total_stake_value = 0
                for contract, tau_value in stake_tau.items():
                    tmp_msg += f"<code>{contract}\n{tau_value:,} TAU</code>\n"
                    total_stake_value += int(tau_value)
                    total_tau_value += int(tau_value)

                if total_stake_value > 0:
                    msg += f"<b>Stake Value</b>\n"
                    msg += tmp_msg

        # ---- LP ----

        try:
            user_lp_api = rs.user_lp_balance(address)

            if user_lp_api:
                for contract, user_lp in user_lp_api["points"].items():
                    for staked_contract, staked_amount in staked_lp.items():
                        if staked_contract == contract:
                            user_lp = float(user_lp) + staked_amount
                            break

                    pair_data = rs.get_pairs(contract)[contract]

                    total_lp = pair_data["lp"]
                    lp_share = float(user_lp) / float(total_lp) * 100

                    total_tau_value = float(pair_data["reserves"][0]) * 2
                    tau_value_share = total_tau_value / 100 * lp_share

                    if int(tau_value_share) == 0:
                        continue

                    lp_tau[contract] = int(tau_value_share)

                tmp_msg = str()
                total_lp_value = 0
                for contract, tau_value in lp_tau.items():
                    tmp_msg += f"<code>{contract}\n{tau_value:,} TAU</code>\n"
                    total_lp_value += tau_value
                    total_tau_value += tau_value

                if total_lp_value > 0:
                    msg += "<b>LP Value</b>\n"
                    msg += tmp_msg
        except:
            pass

        # ---- TOKENS ----

        lamden = Connect()

        try:
            balances = rs.balances(address)

            for contract, balance in balances["balances"].items():
                if contract == "currency":
                    token_tau["currency"] = int(float(balance))
                else:
                    tau_price = lamden.get_contract_variable(
                        self.config.get("rocketswap_contract"),
                        "prices",
                        contract
                    )

                    tau_price = tau_price["value"] if "value" in tau_price else 0
                    tau_price = float(str(tau_price)) if tau_price else float("0")

                    token_tau[contract] = int(float(balance) * tau_price)

            total_token_value = 0
            for contract, tau_value in token_tau.items():
                total_token_value += tau_value
                total_tau_value += tau_value

            if total_token_value > 0:
                msg += f"\n<b>Remaining Token Value</b>\n"
                msg += f"<code>{int(total_token_value):,} TAU</code>\n"
        except Exception as e:
            logging.error(e)

        data = CoinGeckoAPI().get_coin_by_id(self.CGID)

        usd = int(float(data["market_data"]["current_price"]["usd"]) * total_tau_value)
        eur = int(float(data["market_data"]["current_price"]["eur"]) * total_tau_value)
        btc = float(data["market_data"]["current_price"]["btc"]) * total_tau_value
        eth = float(data["market_data"]["current_price"]["eth"]) * total_tau_value

        price_msg = f"<b>Total Value</b>\n" \
                    f"<code>" \
                    f"TAU {int(total_tau_value):,}\n" \
                    f"USD {usd:,}\n" \
                    f"EUR {eur:,}\n" \
                    f"BTC {btc:,.5}\n" \
                    f"ETH {eth:,.4}" \
                    f"</code>"

        message.edit_text(
            f"<b>Account LP Summary\n       By COLLIDER</b>\n\n{msg}\n{price_msg}",
            parse_mode=ParseMode.HTML
        )
