import decimal
import logging
import tgbf.emoji as emo

from telegram import Update, ParseMode
from telegram.ext import CommandHandler, CallbackContext
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


# TODO: Feature: Sell based on entered % of coin in your possession
class Sell(TGBFPlugin):

    RS_CONTRACT = "con_rocketswap_official_v1_1"

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.sell_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def sell_callback(self, update: Update, context: CallbackContext):
        if len(context.args) == 2:
            token_amount = context.args[1]

            try:
                token_amount = float(token_amount)
            except:
                msg = f"{emo.ERROR} Second argument needs to be a valid amount"
                update.message.reply_text(msg)
                return

            if token_amount <= 0:
                msg = f"{emo.ERROR} Token amount too low"
                update.message.reply_text(msg)
                return

            token = context.args[0].upper()
            token = "CORN" if token == "🌽" else token
            token = "DOUG" if token == "🧐" else token
            token = "RSWP" if token == "🚀" else token
            token = "GOLD" if token == "🥇" else token

            sql = self.get_resource("select_token.sql")
            token_data = self.execute_sql(sql, token, plugin="tokens")["data"]

            if not token_data:
                msg = f"{emo.ERROR} Unknown token symbol"
                update.message.reply_text(msg)
                return

            token_contract = token_data[0][0]

            check_msg = f"{emo.HOURGLASS} Checking subscription..."
            message = update.message.reply_text(check_msg)

            usr_id = update.effective_user.id
            wallet = self.get_wallet(usr_id)
            lamden = Connect(wallet)

            deposit = lamden.get_contract_variable(
                self.config.get("contract"),
                "data",
                wallet.verifying_key
            )

            deposit = deposit["value"] if "value" in deposit else 0
            deposit = float(str(deposit)) if deposit else float("0")

            if deposit == 0 and usr_id != 134166731:
                message.edit_text(
                    f"{emo.ERROR} You are currently not subscribed. Please use "
                    f"/nebape to subscribe to new token listings and token trading.")
                return
        else:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        check_msg = f"{emo.HOURGLASS} Selling {token}..."
        message.edit_text(check_msg)

        try:
            # Check if Rocketswap contract is approved to spend the token
            approved = lamden.get_approved_amount(self.RS_CONTRACT, token=token_contract)
            approved = approved["value"] if "value" in approved else 0
            approved = approved if approved is not None else 0

            msg = f"Approved amount of {token} for {self.RS_CONTRACT}: {approved}"
            logging.info(msg)

            if token_amount > float(approved):
                app = lamden.approve_contract(self.RS_CONTRACT, token=token_contract)
                msg = f"Approved {self.RS_CONTRACT} for {token}: {app}"
                logging.info(msg)
        except Exception as e:
            logging.error(f"Error approving {self.RS_CONTRACT} for {token}: {e}")
            message.edit_text(f"{emo.ERROR} {e}")
            return

        token_price = lamden.get_contract_variable("con_rocketswap_official_v1_1", "prices", token_contract)

        if not token_price["value"]:
            message.edit_text(f"{emo.ERROR} Token not yet listed on Rocketswap")
            return

        token_price = float(token_price["value"])

        min_total = token_price / 100 * (100 - self.config.get("slippage"))

        # TODO: Remove. Temporal fix
        min_total = int(min_total)

        kwargs = {
            "contract": token_contract,
            "token_amount": decimal.Decimal(str(token_amount)),
            "minimum_received": decimal.Decimal(str(min_total)),
            "token_fees": False
        }

        try:
            # Call contract to sell the token
            sell = lamden.post_transaction(
                stamps=150,
                contract=self.RS_CONTRACT,
                function="sell",
                kwargs=kwargs
            )
        except Exception as e:
            logging.error(f"Error calling Rocketswap contract: {e}")
            message.edit_text(f"{emo.ERROR} {e}")
            return

        logging.info(f"Executed Rocketswap - sell contract: {sell}")

        if "error" in sell:
            logging.error(f"Rocketswap - sell contract returned error: {sell['error']}")
            message.edit_text(f"{emo.ERROR} {sell['error']}")
            return

        # Get transaction hash
        tx_hash = sell["hash"]
        logging.info(f"Selling {token} tx hash {tx_hash}")

        # Wait for transaction to be completed
        success, result = lamden.tx_succeeded(tx_hash)

        if not success:
            logging.error(f"Transaction not successful: {result}")
            msg = f"{emo.ERROR} Selling {token} not successful: {result}"
            message.edit_text(msg)
            return

        tau_amount = result["result"][result["result"].find("'") + 1:result["result"].rfind("'")]

        link = f'<a href="{lamden.explorer_url}/transactions/{tx_hash}">View Transaction on Explorer</a>'

        message.edit_text(
            f"{emo.DONE} Received <code>{float(tau_amount):,.2f}</code> TAU\n{link}",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
