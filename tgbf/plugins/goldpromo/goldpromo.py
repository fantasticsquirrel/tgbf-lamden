import json
import logging
import tgbf.emoji as emo

from telegram import Update, ParseMode
from telegram.ext import CommandHandler, CallbackContext
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Goldpromo(TGBFPlugin):

    def load(self):
        if not self.table_exists("goldpromo"):
            sql = self.get_resource("create_goldpromo.sql")
            self.execute_sql(sql)

        self.add_handler(CommandHandler(
            self.handle,
            self.goldpromo_callback,
            run_async=True))

    @TGBFPlugin.private
    @TGBFPlugin.send_typing
    def goldpromo_callback(self, update: Update, context: CallbackContext):
        if len(context.args) == 1 and context.args[0].lower() == "winner":
            sql = self.get_resource("select_addresses.sql")
            res = self.execute_sql(sql)

            if not res["data"]:
                update.message.reply_text(
                    f"{emo.ERROR} No addresses found",
                    parse_mode=ParseMode.MARKDOWN)
                return

            msg = f"{emo.HOURGLASS} Selecting winner..."
            message = update.message.reply_text(msg)

            address_list = list()
            for address in res["data"]:
                address_list.append(address[0])

            usr_id = update.effective_user.id
            wallet = self.get_wallet(usr_id)
            lamden = Connect(wallet=wallet)

            contract = self.config.get("contract")
            function = self.config.get("function")

            try:
                # Call contract
                promo = lamden.post_transaction(
                    stamps=100,
                    contract=contract,
                    function=function,
                    kwargs={"addresses": address_list}
                )
            except Exception as e:
                logging.error(f"Error calling goldpromo contract: {e}")
                message.edit_text(f"{emo.ERROR} {e}")
                return

            logging.info(f"Executed goldpromo contract: {promo}")

            if "error" in promo:
                logging.error(f"Goldpromo contract returned error: {promo['error']}")
                message.edit_text(f"{emo.ERROR} {promo['error']}")
                return

            # Get transaction hash
            tx_hash = promo["hash"]

            # Wait for transaction to be completed
            success, result = lamden.tx_succeeded(tx_hash)

            if not success:
                logging.error(f"Goldpromo transaction not successful: {result}")
                message.edit_text(f"{emo.ERROR} {result}")
                return

            ex_link = f'<a href="{lamden.explorer_url}/transactions/{tx_hash}">View Transaction on Explorer</a>'

            winner = json.loads(result["result"].replace("'", '"'))

            message.edit_text(
                f"<code>"
                f"Address:\n{winner['address']}\n\n"
                f"Balance:\n{winner['balance']}\n\n"
                f"Stake:\n{winner['stake']}\n\n"
                f"LP-Stake:\n{winner['lp_stake']}\n\n"
                f"</code>"
                f"{ex_link}",
                parse_mode=ParseMode.HTML
            )
            return

        if len(context.args) != 1:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        address = context.args[0]

        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet=wallet)

        if not lamden.is_address_valid(address):
            update.message.reply_text(f"{emo.ERROR} Address not valid")
            return

        sql = self.get_resource("select_address.sql")
        res = self.execute_sql(sql, address)

        if res["data"]:
            update.message.reply_text(f"{emo.ERROR} Address already added")
            return

        sql = self.get_resource("insert_address.sql")
        res = self.execute_sql(sql, usr_id, address)

        if not res["success"]:
            update.message.reply_text(f"{emo.ERROR} {res['data']}")
            return

        update.message.reply_text(f"{emo.DONE} Address added")
