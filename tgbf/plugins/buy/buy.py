import logging
import tgbf.emoji as emo

from telegram import Update, ParseMode
from telegram.ext import CommandHandler, CallbackContext
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


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

            # ----------------------

            # TODO: Remove. Temporal fix
            if tau_amount.is_integer():
                tau_amount = int(tau_amount)
            else:
                msg = f"{emo.ERROR} Amount currently needs to be an Integer"
                update.message.reply_text(msg)
                return

            # ----------------------

            if tau_amount <= 0:
                msg = f"{emo.ERROR} Amount of TAU too low"
                update.message.reply_text(msg)
                return

            token = context.args[0].upper()

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
                    f"/goldape to subscribe to new token listings and token trading.")
                return
        else:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        check_msg = f"{emo.HOURGLASS} Buying {token}..."
        message.edit_text(check_msg)

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
        token_price = float(token_price["value"])

        token_amount_to_buy = tau_amount / token_price
        min_token_amount = token_amount_to_buy / 100 * (100 - self.config.get("slippage"))

        # TODO: Remove. Temporal fix
        min_token_amount = int(min_token_amount)

        kwargs = {
            "contract": token_contract,
            "currency_amount": tau_amount,
            "minimum_received": min_token_amount,
            "token_fees": False
        }

        try:
            # Call contract to buy the token
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
        logging.info(f"Buying {token} tx hash {tx_hash}")

        # Wait for transaction to be completed
        success, result = lamden.tx_succeeded(tx_hash)

        if not success:
            logging.error(f"Transaction not successful: {result}")
            msg = f"{emo.ERROR} Buying {token} not successful: {result}"
            message.edit_text(msg)
            return

        bought_amount = result["result"][result["result"].find("'") + 1:result["result"].rfind("'")]

        message.edit_text(
            f"{emo.DONE} Received <code>{int(float(bought_amount)):,}</code> {token}",
            parse_mode=ParseMode.HTML
        )
