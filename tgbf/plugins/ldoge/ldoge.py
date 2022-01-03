import html
import logging
import tgbf.emoji as emo
import tgbf.utils as utl

from telegram import ParseMode, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from telegram.utils.helpers import escape_markdown
from tgbf.plugin import TGBFPlugin


class Ldoge(TGBFPlugin):

    def load(self):
        if not self.table_exists("stories"):
            sql = self.get_resource("create_stories.sql")
            self.execute_sql(sql)
        if not self.table_exists("votes"):
            sql = self.get_resource("create_votes.sql")
            self.execute_sql(sql)

        self.add_handler(CommandHandler(
            self.name,
            self.ldoge_callback,
            run_async=True))

        self.add_handler(CallbackQueryHandler(
            self.button_callback,
            run_async=True))

    @TGBFPlugin.private
    @TGBFPlugin.send_typing
    def ldoge_callback(self, update: Update, context: CallbackContext):
        channel_link = self.config.get("channel_link")

        if len(context.args) == 0:
            update.message.reply_text(
                self.get_usage({'{{tgchannel}}': escape_markdown(channel_link)}),
                parse_mode=ParseMode.MARKDOWN)
            return

        usr = update.effective_user

        user_id = usr.id
        user_full_name = usr.full_name
        user_username = usr.username
        user_story = update.message.text.replace(f"/{self.handle} ", "")

        user_story = html.escape(user_story)

        smin = self.config.get("min_chars")
        smax = self.config.get("max_chars")

        # Check if story has more than min length and less than max length
        if smin > len(user_story) or len(user_story) > smax:
            update.message.reply_text(
                f"{emo.ERROR} Your story needs to have more than {smin} "
                f"characters and less than {smax} characters to be accepted")
            return

        # Check if user already submitted a story
        if self.execute_sql(self.get_resource("check_user.sql"), user_id)["data"]:
            update.message.reply_text(f"{emo.ERROR} You can submit only one story!")
            return

        # Retrieve row ID of current story if it exists
        data = self.execute_sql(self.get_resource("select_rowid.sql"), user_story)["data"]

        # Check if story is already in DB
        if data and data[0]:
            update.message.reply_text(f"{emo.ERROR} This story was already submitted!")
            return

        # Insert user story
        self.execute_sql(
            self.get_resource("insert_story.sql"),
            user_id,
            user_full_name,
            user_username,
            user_story)

        # Retrieve row ID again since it can only be empty right now
        data = self.execute_sql(self.get_resource("select_rowid.sql"), user_story)["data"]

        try:
            # Send story to 'LDOGE Stories' channel
            context.bot.send_message(
                self.config.get("channel"),
                escape_markdown(user_story),
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_buttons(update.effective_user.id, data[0][0]))

            link = f'<a href="{channel_link}">LDOGE Stories</a>'

            update.message.reply_text(
                f"{emo.DONE} Story successfully submitted to {link}",
                parse_mode=ParseMode.HTML)
        except Exception as e:
            logging.info(f"User {user_id} could not be notified about LDOGE reply: {e} - {update}")
            update.message.reply_text(f'{emo.ERROR} Error while saving story: {e}')

    def button_callback(self, update: Update, context: CallbackContext):
        data = update.callback_query.data

        if not data.startswith(self.name):
            return

        data_list = data.split("|")

        if not data_list:
            return

        if len(data_list) != 4:
            return

        if int(data_list[1]) != update.effective_user.id:
            return

        action = data_list[2]
        story_id = data_list[3]
        user_id = update.effective_user.id

        self.execute_sql(self.get_resource("delete_vote.sql"), story_id, user_id)

        if action == "UP":
            self.execute_sql(
                self.get_resource("insert_vote.sql"),
                story_id,
                user_id,
                1)

        elif action == "DOWN":
            self.execute_sql(
                self.get_resource("insert_vote.sql"),
                story_id,
                user_id,
                -1)

        msg = f"{emo.STARS} Vote counted!"
        context.bot.answer_callback_query(update.callback_query.id, msg)
        return

    def get_buttons(self, user_id, row_id):
        menu = utl.build_menu([
            InlineKeyboardButton(f"{emo.UP} Vote Up", callback_data=f"{self.name}|{user_id}|UP|{row_id}"),
            InlineKeyboardButton(f"{emo.DOWN} Vote Down", callback_data=f"{self.name}|{user_id}|DOWN|{row_id}")
        ], n_cols=2)
        return InlineKeyboardMarkup(menu, resize_keyboard=True)
