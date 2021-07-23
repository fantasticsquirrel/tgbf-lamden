import tgbf.emoji as emo
import tgbf.utils as utl

from telegram import Update, ParseMode
from telegram.ext import CommandHandler, CallbackContext
from tgbf.lamden.rocketswap import Rocketswap
from tgbf.lamden.connect import Connect
from pycoingecko import CoinGeckoAPI
from tgbf.lamden.api import API
from tgbf.plugin import TGBFPlugin


class Account(TGBFPlugin):

    CGID = "lamden"
    RS_CONTRACT = "con_rocketswap_official_v1_1"

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.account_callback,
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

        #lamden = Connect()
        rs = Rocketswap()

        lp_tau = dict()
        for contract, user_lp in rs.user_lp_balance(address)["points"].items():
            pair_data = rs.get_pairs(contract)[contract]

            total_lp = pair_data["lp"]
            lp_share = float(user_lp) / float(total_lp) * 100

            total_tau_value = float(pair_data["reserves"][0]) * 2
            tau_value_share = total_tau_value / 100 * lp_share

            if int(tau_value_share) == 0:
                continue

            lp_tau[contract] = int(tau_value_share)

        msg = str()
        total_tau_value = 0
        for contract, tau_value in lp_tau.items():
            msg += f"\n<code>{contract}\n{tau_value:,} TAU</code>\n"
            total_tau_value += tau_value

        data = CoinGeckoAPI().get_coin_by_id(self.CGID)

        usd = int(float(data["market_data"]["current_price"]["usd"]) * total_tau_value)
        eur = int(float(data["market_data"]["current_price"]["eur"]) * total_tau_value)
        btc = float(data["market_data"]["current_price"]["btc"]) * total_tau_value
        eth = float(data["market_data"]["current_price"]["eth"]) * total_tau_value

        price_msg = f"<b>Total Value</b>\n" \
                    f"<code>" \
                    f"TAU {total_tau_value:,}\n" \
                    f"USD {usd:,}\n" \
                    f"EUR {eur:,}\n" \
                    f"BTC {btc:,.5}\n" \
                    f"ETH {eth:,.4}" \
                    f"</code>"

        update.message.reply_text(
            f"<b>Account LP Summary</b>\n{msg}\n{price_msg}",
            parse_mode=ParseMode.HTML
        )

        """
        staking_meta = rs.staking_meta()

        stake_tau = dict()
        for staking_contract, staking_data in rs.user_staking_info(address).items():
            yield_info = staking_data["yield_info"]

            if not yield_info:
                continue

            total_staked = yield_info["total_staked"]

            if total_staked == 0:
                continue

            #stake_token_contract = staking_meta["contract_name"]["meta"]["STAKING_TOKEN"]

            for staking_meta_data in staking_meta["ents"]:
                if staking_meta_data["contract_name"] == staking_contract:
                    if token_price and token_price["value"]:
                        stake_tau [stake_token_contract] =
                            token_price["value"]
        """

    def get_amount_lhc(self):
        lhc_price = Connect().get_contract_variable(
            self.config.get("rocketswap_contract"),
            "prices",
            self.config.get("lhc_contract")
        )

        lhc_price = lhc_price["value"] if "value" in lhc_price else 0
        lhc_price = float(str(lhc_price)) if lhc_price else float("0")

        tau_price = self.config.get("tau_price")

        return tau_price / lhc_price
