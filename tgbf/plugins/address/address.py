import io
import segno
import tgbf.emoji as emo
import tgbf.utils as utl
import qrcode_artistic

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from telegram import ParseMode
from tgbf.plugin import TGBFPlugin


class Address(TGBFPlugin):

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.address_callback,
            run_async=True))

        self.add_handler(CallbackQueryHandler(
            self.privkey_callback,
            run_async=True))

    @TGBFPlugin.blacklist
    @TGBFPlugin.send_typing
    def address_callback(self, update: Update, context: CallbackContext):
        wallet = self.get_wallet(update.effective_user.id)

        b_out = io.BytesIO()
        if context.args and context.args[0].lower() == "profile":
            photos = context.bot.getUserProfilePhotos(update.effective_user.id)

            if photos.photos:
                for photo in photos.photos:
                    img = photo[-1].get_file().download(out=io.BytesIO())
                    qr = segno.make_qr(wallet.verifying_key)
                    qr.to_artistic(background=img, target=b_out, border=1, scale=10, kind='png')
                    break
            else:
                segno.make_qr(wallet.verifying_key).save(b_out, border=1, scale=10, kind="png")
        else:
            segno.make_qr(wallet.verifying_key).save(b_out, border=1, scale=10, kind="png")

        if self.is_private(update.message):
            update.message.reply_photo(
                photo=b_out.getvalue(),
                caption=f"`{wallet.verifying_key}`",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=self.privkey_button_callback(wallet.signing_key))
        else:
            update.message.reply_photo(
                photo=b_out.getvalue(),
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
