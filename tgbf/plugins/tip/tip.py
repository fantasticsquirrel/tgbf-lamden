import logging
import tgbf.emoji as emo
import tgbf.utils as utl

from telegram import ParseMode, Update
from lamden.crypto.wallet import Wallet
from telegram.ext import CommandHandler, CallbackContext
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Tiptrx(TGBFPlugin):

    def load(self):
        if not self.table_exists("tips"):
            sql = self.get_resource("create_tips.sql")
            self.execute_sql(sql)

        self.add_handler(CommandHandler(
            self.name,
            self.tip_callback,
            run_async=True),
            group=1)

    @TGBFPlugin.public
    @TGBFPlugin.send_typing
    def tip_callback(self, update: Update, context: CallbackContext):
        if len(context.args) != 1:
            update.message.reply_text(
                text=f"Usage:\n{self.get_usage()}",
                parse_mode=ParseMode.MARKDOWN)
            return

        reply = update.message.reply_to_message

        if not reply:
            msg = f"{emo.ERROR} Tip a user by replying to his message"
            logging.error(f"{msg} - {update}")
            update.message.reply_text(msg)
            return

        amount = context.args[0]
        to_user_id = reply.from_user.id
        from_user_id = update.effective_user.id

        try:
            # Check if amount is valid
            amount = float(amount)
        except:
            msg = f"{emo.ERROR} Provided amount is not valid"
            logging.error(f"{msg} - {update}")
            update.message.reply_text(msg)
            return

        # Get wallet from which we want to tip
        sql = self.get_resource("select_wallet.sql", plugin="wallets")
        res = self.execute_sql(sql, from_user_id, plugin="wallets")

        if not res["data"]:
            msg = f"{emo.ERROR} Can't retrieve your wallet"
            update.message.reply_text(msg)
            self.notify(msg)
            return

        from_wallet = Wallet(res["data"][0][2])
        lamden = Connect(wallet=from_wallet)

        # Get wallet to which we want to tip
        sql = self.get_resource("select_wallet.sql", plugin="wallets")
        res = self.execute_sql(sql, to_user_id, plugin="wallets")

        if res["data"]:
            to_address = res["data"][0][1]
        else:
            # TODO: Save new wallet address to db
            to_address = Wallet().verifying_key

        try:
            # TODO: Which type to use?
            tip = lamden.post_transaction(from_wallet, amount, to_address)

            logging.info(f"Tipped {amount} TAU from {from_user_id} to {to_user_id}: {tip}")

            tx_hash = tip["hash"]

            # Insert details into database
            sql = self.get_resource("insert_tip.sql")
            self.execute_sql(sql, from_user_id, to_user_id, amount, tx_hash)

            if amount.is_integer():
                amount = int(amount)

            if reply.from_user.username:
                to_user = f"@{reply.from_user.username}"
            else:
                to_user = reply.from_user.first_name

            if update.effective_user.username:
                from_user = f"@{update.effective_user.username}"
            else:
                from_user = update.effective_user.first_name

            ex_url = lamden.cfg.get("explorer", lamden.chain)

            update.message.reply_text(
                f"{emo.DONE} {utl.esc_md(to_user)} received `{amount}` TAU\n"
                f"[View on Explorer]({ex_url}/transactions/{tx_hash})",
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True)

            try:
                # Notify user about tip
                context.bot.send_message(
                    to_user_id,
                    f"You received `{amount}` TAU from {utl.esc_md(from_user)}\n"
                    f"[View on Explorer]({ex_url}/transactions/{tx_hash})",
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True)
                logging.info(f"User {to_user_id} notified about tip of {amount} TAU")
            except Exception as e:
                logging.info(f"User {to_user_id} could not be notified about tip: {e}")
        except Exception as e:
            msg = f"{emo.ERROR} Could not tip TAU: {e}"
            logging.error(f"{msg} - {update}")
            update.message.reply_text(msg)
