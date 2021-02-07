import os
import tgbf.emoji as emo
import tgbf.utils as utl
import tgbf.constants as con

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from telegram import ParseMode
from tgbf.plugin import TGBFPlugin
from MyQR import myqr


class Address(TGBFPlugin):

    QRCODES_DIR = "qr_codes"
    LAMDEN_LOGO = "logo.png"

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.address_callback,
            run_async=True),
            group=1)

        self.add_handler(CallbackQueryHandler(
            self.privkey_callback,
            run_async=True),
            group=1)

    @TGBFPlugin.send_typing
    def address_callback(self, update: Update, context: CallbackContext):
        sql = self.get_resource("select_wallet.sql", plugin="wallets")
        res = self.execute_sql(sql, update.effective_user.id, plugin="wallets")

        if not res["data"]:
            msg = f"{emo.ERROR} Can't retrieve your wallet"
            update.message.reply_text(msg)
            self.notify(msg)
            return

        address = res["data"][0][1]
        privkey = res["data"][0][2]

        # Create directory for qr-code images
        qr_dir = os.path.join(self.get_plg_path(), self.QRCODES_DIR)
        os.makedirs(qr_dir, exist_ok=True)

        # Get file and path of qr-code image
        qr_name = f"{update.effective_user.id}.png"
        qr_code = os.path.join(qr_dir, qr_name)

        if not os.path.isfile(qr_code):
            logo = os.path.join(self.get_plg_path(), con.DIR_RES, self.LAMDEN_LOGO)

            myqr.run(
                address,
                version=1,
                level='H',
                picture=logo,
                colorized=True,
                contrast=1.0,
                brightness=1.0,
                save_name=qr_name,
                save_dir=qr_dir)

        with open(qr_code, "rb") as qr_pic:
            if self.is_private(update.message):
                update.message.reply_photo(
                    photo=qr_pic,
                    caption=f"`{address}`",
                    parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=self.privkey_button_callback(privkey))
            else:
                update.message.reply_photo(
                    photo=qr_pic,
                    caption=f"`{address}`",
                    parse_mode=ParseMode.MARKDOWN_V2)

    def privkey_callback(self, update: Update, context: CallbackContext):
        query = update.callback_query
        message = query.message

        message.edit_caption(
            caption=f"*Address*\n`{message.caption}`\n\n*Private Key*\n`{query.data}`",
            parse_mode=ParseMode.MARKDOWN_V2)

        msg = f"{emo.ALERT} DELETE AFTER VIEWING {emo.ALERT}"
        context.bot.answer_callback_query(query.id, msg)

    def privkey_button_callback(self, privkey):
        menu = utl.build_menu([InlineKeyboardButton("Show Private Key", callback_data=privkey)])
        return InlineKeyboardMarkup(menu, resize_keyboard=True)
