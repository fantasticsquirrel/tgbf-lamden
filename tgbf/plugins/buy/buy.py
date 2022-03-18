import decimal
import logging
import tgbf.emoji as emo

from telegram import Update, ParseMode
from telegram.ext import CommandHandler, CallbackContext
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


# TODO: Feature: Sell based on entered % of coin in your possession
class Buy(TGBFPlugin):

    RS_CONTRACT = "con_rocketswap_official_v1_1"

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.buy_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def buy_callback(self, update: Update, context: CallbackContext):
        if len(context.args) == 2:
            tau_amount = context.args[1]

            try:
                tau_amount = float(tau_amount)
            except:
                msg = f"{emo.ERROR} Second argument needs to be a valid amount"
                update.message.reply_text(msg)
                return

            if tau_amount <= 0:
                msg = f"{emo.ERROR} Amount of TAU too low"
                update.message.reply_text(msg)
                return

            token = context.args[0].upper()
            token = "CORN" if token == "🌽" else token
            token = "DOUG" if token == "🧐" else token
            token = "RSWP" if token == "🚀" else token
            token = "GOLD" if token == "🥇" else token
            token = "BEER" if token == "🍺" else token

            sql = self.get_resource("select_token.sql")
            token_data = self.execute_sql(sql, token, plugin="tokens")["data"]

            if not token_data:
                msg = f"{emo.ERROR} Unknown token symbol"
                update.message.reply_text(msg)
                return

            token_contract = token_data[0][0]

            usr_id = update.effective_user.id
            wallet = self.get_wallet(usr_id)
            lamden = Connect(wallet)

            check_msg = f"{emo.HOURGLASS} Checking subscription..."
            message = update.message.reply_text(check_msg)

            buying_msg = f"{emo.HOURGLASS} Buying {token}..."

            if token_contract not in ["con_nebula", "con_collider_contract"]:
                deposit = lamden.get_contract_variable(
                    self.config.get("contract"),
                    "data",
                    wallet.verifying_key
                )

                deposit = deposit["value"] if "value" in deposit else 0
                deposit = float(str(deposit)) if deposit else float("0")

                if deposit == 0 and usr_id not in self.config.get("whitelist"):
                    message.edit_text(
                        f"{emo.ERROR} You are currently not subscribed. Please use "
                        f"/nebape to subscribe to new token listings and token trading.")
                    return

                message.edit_text(buying_msg)
            else:
                message.edit_text(buying_msg)
        else:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        try:
            # Check if Rocketswap contract is approved to spend TAU
            approved = lamden.get_approved_amount(self.RS_CONTRACT)
            approved = approved["value"] if "value" in approved else 0
            approved = approved if approved is not None else 0

            msg = f"Approved amount of TAU for {self.RS_CONTRACT}: {approved}"
            logging.info(msg)

            if tau_amount > float(approved):
                app = lamden.approve_contract(self.RS_CONTRACT)
                msg = f"Approved {self.RS_CONTRACT} for TAU: {app}"
                logging.info(msg)
        except Exception as e:
            logging.error(f"Error approving {self.RS_CONTRACT} for TAU: {e}")
            message.edit_text(f"{emo.ERROR} {e}")
            return

        token_price = lamden.get_contract_variable("con_rocketswap_official_v1_1", "prices", token_contract)

        if not token_price["value"]:
            message.edit_text(f"{emo.ERROR} Token not yet listed on Rocketswap")
            return

        token_price = float(token_price["value"])

        token_amount_to_buy = tau_amount / token_price
        min_token_amount = token_amount_to_buy / 100 * (100 - self.config.get("slippage"))

        kwargs = {
            "contract": token_contract,
            "currency_amount": decimal.Decimal(str(tau_amount)),
            "minimum_received": decimal.Decimal(str(min_token_amount)),
            "token_fees": False
        }

        try:
            # Call contract to buy the token
            buy = lamden.post_transaction(
                stamps=300,
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
        logging.info(f"Buying {token} tx hash {tx_hash}")

        # Wait for transaction to be completed
        success, result = lamden.tx_succeeded(tx_hash)

        if not success:
            logging.error(f"Transaction not successful: {result}")
            msg = f"{emo.ERROR} Buying {token} not successful: {result}"
            message.edit_text(msg)
            return

        bought_amount = result["result"][result["result"].find("'") + 1:result["result"].rfind("'")]

        link = f'<a href="{lamden.explorer_url}/transactions/{tx_hash}">View Transaction on Explorer</a>'

        message.edit_text(
            f"{emo.DONE} Received <code>{float(bought_amount):,.2f}</code> {token}\n{link}",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
