import logging
import tgbf.emoji as emo

from telegram import Update, ParseMode
from telegram.ext import CommandHandler, CallbackContext
from tgbf.lamden.rocketswap import Rocketswap
from tgbf.lamden.connect import Connect
from tgbf.lamden.api import API
from tgbf.plugin import TGBFPlugin


class Account(TGBFPlugin):

    RS_CONTRACT = "con_rocketswap_official_v1_1"

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.account_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def account_callback(self, update: Update, context: CallbackContext):
        if len(context.args) == 0:
            usr_id = update.effective_user.id
            wallet = self.get_wallet(usr_id)
            address = wallet.verifying_key

        elif len(context.args) == 1:
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
        for contract, user_lp in rs.user_lp_balance(address)["points"]:
            pair_data = rs.get_pairs(contract)[contract]

            total_lp = pair_data["lp"]
            lp_share = user_lp / total_lp * 100

            total_tau_value = pair_data["reserves"][0] * 2
            tau_value_share = total_tau_value / 100 * lp_share

            lp_tau[contract] = tau_value_share

        staking_meta = rs.staking_meta()

        stake_tau = dict()
        for staking_contract, staking_data in rs.user_staking_info(address):
            total_staked = staking_data["yield_info"]["total_staked"]

            if total_staked == 0:
                continue

            #stake_token_contract = staking_meta["contract_name"]["meta"]["STAKING_TOKEN"]

            for staking_meta_data in staking_meta["ents"]:
                if staking_meta_data["contract_name"] == staking_contract:
                    """
                    if token_price and token_price["value"]:
                        stake_tau [stake_token_contract] =
                            token_price["value"]
                    """
