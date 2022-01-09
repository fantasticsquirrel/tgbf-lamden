import tgbf.emoji as emo

from telegram import Update, ParseMode
from telegram.ext import CommandHandler, CallbackContext
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Addressbook(TGBFPlugin):

    def load(self):
        if not self.table_exists("addressbook"):
            sql = self.get_resource("create_addressbook.sql")
            self.execute_sql(sql)

        self.add_handler(CommandHandler(
            self.handle,
            self.addressbook_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def addressbook_callback(self, update: Update, context: CallbackContext):
        if len(context.args) != 1:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        alias_address = context.args[0]

        if not "=" in alias_address:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        alias_array = alias_address.split("=")

        if len(alias_array) != 3:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet)

        alias = address = ""

        if lamden.is_address_valid(alias_array[0]):
            address = alias_array[0]
            alias = alias_array[2]

        if not address:
            update.message.reply_text(f"{emo.ERROR} Provided address is not valid!")
            return

        if not alias:
            update.message.reply_text(f"{emo.ERROR} Provided alias is not valid!")
            return

        self.execute_sql(
            self.get_resource("insert_alias.sql"),
            update.effective_user.id,
            alias,
            address)

        update.message.reply_text(f"{emo.DONE} Alias saved")
