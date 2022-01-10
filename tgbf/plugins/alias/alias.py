import tgbf.emoji as emo
import tgbf.utils as utl

from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Alias(TGBFPlugin):

    def load(self):
        if not self.table_exists("aliases"):
            sql = self.get_resource("create_aliases.sql")
            self.execute_sql(sql)

        self.add_handler(CommandHandler(
            self.handle,
            self.alias_callback,
            run_async=True))

        self.add_handler(CallbackQueryHandler(
            self.button_callback,
            run_async=True))

    @TGBFPlugin.private
    @TGBFPlugin.send_typing
    def alias_callback(self, update: Update, context: CallbackContext):
        if len(context.args) != 1:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        arg = context.args[0]

        if arg.lower() == "list":
            aliases = self.execute_sql(self.get_resource("select_aliases.sql"))

            if aliases["data"]:
                for alias in aliases["data"]:
                    update.message.reply_text(
                        f"<code>{alias[0]}</code>=<code>{alias[1]}</code>",
                        reply_markup=self.get_remove_button(update.effective_user.id, alias[0]),
                        parse_mode=ParseMode.HTML)
                return
            else:
                update.message.reply_text(f"{emo.ERROR} No aliases found")
            return

        if "=" not in arg:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        alias_array = arg.split("=")

        if len(alias_array) != 2:
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
            alias = alias_array[1]
        elif lamden.is_address_valid(alias_array[1]):
            address = alias_array[1]
            alias = alias_array[0]

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

    def get_remove_button(self, user_id, alias):
        menu = utl.build_menu([
            InlineKeyboardButton(f"{emo.STOP} Remove alias", callback_data=f"{self.name}|{user_id}|{alias}")
        ])
        return InlineKeyboardMarkup(menu, resize_keyboard=True)

    def button_callback(self, update: Update, context: CallbackContext):
        data = update.callback_query.data

        if not data.startswith(self.name):
            return

        data_list = data.split("|")

        if not data_list:
            return

        if len(data_list) != 3:
            return

        user_id = update.effective_user.id

        if data_list[1] != user_id:
            return

        alias = data_list[2]

        self.execute_sql(self.get_resource("delete_alias.sql"), alias)

        context.bot.delete_message(
            update.effective_user.id,
            update.callback_query.message.message_id)

        msg = f"{emo.DONE} Alias '{alias}' removed!"
        context.bot.answer_callback_query(update.callback_query.id, msg)
