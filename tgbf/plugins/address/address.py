import io
import segno
import tgbf.emoji as emo
import tgbf.utils as utl

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from telegram import ParseMode
from tgbf.plugin import TGBFPlugin


class Address(TGBFPlugin):

    QRCODES_DIR = "qr_codes"
    LAMDEN_LOGO = "logo.png"

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.address_callback,
            run_async=True))

        self.add_handler(CallbackQueryHandler(
            self.privkey_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def address_callback(self, update: Update, context: CallbackContext):
        wallet = self.get_wallet(update.effective_user.id)

        buff = io.BytesIO()
        segno.make_qr(wallet.verifying_key).save(buff, kind="png", border=1, scale=10)

        if self.is_private(update.message):
            update.message.reply_photo(
                photo=buff.getvalue(),
                caption=f"`{wallet.verifying_key}`",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=self.privkey_button_callback(wallet.signing_key))
        else:
            update.message.reply_photo(
                photo=buff.getvalue(),
                caption=f"`{wallet.verifying_key}`",
                parse_mode=ParseMode.MARKDOWN_V2)

    def privkey_callback(self, update: Update, context: CallbackContext):
        query = update.callback_query
        message = query.message

        message.edit_caption(
            caption=f"*Address*\n`{message.caption}`\n\n*Private Key*\n`{query.data}`",
            parse_mode=ParseMode.MARKDOWN_V2)

        msg = f"{emo.WARNING} DELETE AFTER VIEWING {emo.WARNING}"
        context.bot.answer_callback_query(query.id, msg)

    def privkey_button_callback(self, privkey):
        menu = utl.build_menu([InlineKeyboardButton("Show Private Key", callback_data=privkey)])
        return InlineKeyboardMarkup(menu, resize_keyboard=True)
