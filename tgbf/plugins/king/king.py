import os
import logging
import tgbf.emoji as emo
import tgbf.utils as utl

from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class King(TGBFPlugin):

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.king_callback,
            run_async=True))

        self.add_handler(CallbackQueryHandler(
            self.mint_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def king_callback(self, update: Update, context: CallbackContext):
        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet)

        contract = self.config.get("contract")

        context.bot.send_photo(
            update.effective_chat.id,
            open(os.path.join(self.get_res_path(), "pepe.jpg"), "rb"),
            reply_markup=self.get_mint_button())

        try:
            approved = lamden.get_approved_amount(contract)
            approved = approved["value"] if "value" in approved else 0
            approved = approved if approved is not None else 0

            msg = f"Approved amount of TAU for {contract}: {approved}"
            logging.info(msg)

            if 10 > float(approved):
                app = lamden.approve_contract(contract)
                msg = f"Approved {contract}: {app}"
                logging.info(msg)

        except Exception as e:
            logging.error(f"Error approving KING contract: {e}")
            return

    def mint_callback(self, update: Update, context: CallbackContext):
        data = update.callback_query.data

        if data != self.name:
            return

        message = update.callback_query.message

        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet)

        try:
            mint = lamden.post_transaction(
                stamps=self.config.get('stamps_to_use'),
                contract=self.config.get("contract"),
                function="mint",
                kwargs=dict()
            )
        except Exception as e:
            logging.error(f"Error calling KING - mint(): {e}")
            message.edit_caption(f"{emo.ERROR} {e}")
            return

        logging.info(f"Executed KING - mint(): {mint}")

        if "error" in mint:
            logging.error(f"KING - mint() returned error: {mint['error']}")
            message.edit_caption(f"{emo.ERROR} {mint['error']}")
            return

        context.bot.answer_callback_query(update.callback_query.id, f'{emo.DONE} Contract executed')

    def get_mint_button(self):
        menu = utl.build_menu([InlineKeyboardButton("Mint KING", callback_data=f"{self.name}")])
        return InlineKeyboardMarkup(menu, resize_keyboard=True)
