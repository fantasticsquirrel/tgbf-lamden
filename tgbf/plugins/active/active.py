import logging

from telegram import Update

from tgbf.plugin import TGBFPlugin
from telegram.ext import MessageHandler, Filters, CallbackContext


# TODO: Periodically clean up DB
class Active(TGBFPlugin):

    def load(self):
        if not self.table_exists("active"):
            sql = self.get_resource("create_active.sql")
            self.execute_sql(sql)

        # Receive all messages from group and save user_id, user_name and date_time
        self.bot.dispatcher.add_handler(
            MessageHandler(Filters.all & (~Filters.command), self.save),
            group=0)  # TODO: Do i need a group here?

    def save(self, update: Update, context: CallbackContext):
        try:
            c = update.effective_chat

            if c.type.lower() == "private":
                return

            u = update.effective_user

            if not u:
                return
            if u.is_bot:
                return

            sql = self.get_resource("insert_active.sql")
            self.execute_sql(sql, c.id, u.id, "@" + u.username if u.username else u.first_name)
        except Exception as e:
            logging.error(f"ERROR: {e} - UPDATE: {update}")
            self.notify(e)
