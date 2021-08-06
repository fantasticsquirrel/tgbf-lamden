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
        context.user_data.clear()

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
            context.user_data["privkey"] = wallet.signing_key

            update.message.reply_photo(
                photo=b_out.getvalue(),
                caption=f"<code>{wallet.verifying_key}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=self.privkey_button_callback())
        else:
            update.message.reply_photo(
                photo=b_out.getvalue(),
                caption=f"<code>{wallet.verifying_key}</code>",
                parse_mode=ParseMode.HTML)

    def privkey_callback(self, update: Update, context: CallbackContext):
        if update.callback_query.data != self.name:
            return

        if "privkey" not in context.user_data:
            msg = f"Old message. Please execute command again"
            context.bot.answer_callback_query(update.callback_query.id, msg)
            return

        message = update.callback_query.message
        privkey = context.user_data["privkey"]

        message.edit_caption(
            caption=f"<b>Address</b>\n"
                    f"<code>{message.caption}</code>\n\n"
                    f"<b>Private Key</b>\n"
                    f"<code>{privkey}</code>",
            parse_mode=ParseMode.HTML)

        msg = f"{emo.WARNING} DELETE AFTER VIEWING {emo.WARNING}"
        context.bot.answer_callback_query(update.callback_query.id, msg)

    def privkey_button_callback(self):
        menu = utl.build_menu([InlineKeyboardButton("Show Private Key", callback_data=self.name)])
        return InlineKeyboardMarkup(menu, resize_keyboard=True)
