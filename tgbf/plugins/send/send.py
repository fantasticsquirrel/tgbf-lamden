import tgbf.emoji as emo

from telegram import Update
from tgbf.plugin import TGBFPlugin
from tgbf.lamden.wallet import LamdenWallet
from tgbf.lamden.connect import LamdenConnect
from telegram.ext import CommandHandler, CallbackContext


class Send(TGBFPlugin):

    def load(self):
        if not self.table_exists("send"):
            sql = self.get_resource("create_send.sql")
            self.execute_sql(sql)

        self.add_handler(CommandHandler(
            self.name,
            self.send_callback,
            run_async=True),
            group=1)

    def send_callback(self, update: Update, context: CallbackContext):
        sql = self.get_resource("select_wallet.sql", plugin="wallet")
        res = self.execute_sql(sql, update.effective_user.id, plugin="wallet")

        if not res["data"]:
            msg = f"{emo.ERROR} Can't retrieve your wallet"
            update.message.reply_text(msg)
            self.notify(msg)
            return

        wallet = LamdenWallet(res["data"][0][2])
        lamden = LamdenConnect(wallet=wallet)

        print(lamden.get_nonce())
        print(lamden.get_balance(wallet.vk.encode().hex()))

        # TODO: Send transaction

        """
        my_token = client.get_contract('my_token')
        # Call transfer method
        my_token.transfer(
            amount=10,
            receiver='you'
        )
        """
