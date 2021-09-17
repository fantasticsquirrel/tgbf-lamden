import os
import logging
import tgbf.emoji as emo
import tgbf.utils as utl

from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Nebkey(TGBFPlugin):

    STAKE = "STAKE"
    UNSTAKE = "UNSTAKE"
    NEB_KEY_URL = "https://medium.com/@nebulalamden/nebula-key-af809262b26b"

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.nebkey_callback,
            run_async=True))

        self.add_handler(CallbackQueryHandler(
            self.button_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def nebkey_callback(self, update: Update, context: CallbackContext):
        cal_msg = f"{emo.HOURGLASS} Checking NEB stake..."
        mp4_vid = os.path.join(self.get_res_path(), "pepekey.mp4")
        message = update.message.reply_video(open(mp4_vid, "rb"), caption=cal_msg)

        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet)

        staked = lamden.get_contract_variable(
            self.config.get("key_contract"),
            "staking",
            wallet.verifying_key)

        staked = staked["value"] if "value" in staked else ""

        if staked:
            message.edit_caption(
                f"You are currently staking NEB. Hit the 'Unstake' button to get your NEB back "
                f"and mint a KEY token.\n\nBut make sure to be staked at least three weeks or "
                f"otherwise you will get only 99% of your staked NEB back and no KEY token.",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_unstake_button(update.effective_user.id))
        else:
            message.edit_caption(
                f"<b>Stake 1 million NEB to earn 1 KEY token.</b>\n\n"
                f"If you stake 1 million NEB for at least three weeks you will get back 100% of "
                f"your staked NEB and additionally also mint 1 KEY token. If you unstake earlier, "
                f"you will get 99% of your staked NEB back and no KEY token.\n\n"
                f'<a href="{self.NEB_KEY_URL}">Read more about what KEY token is</a>',
                reply_markup=self.get_stake_button(update.effective_user.id),
                parse_mode=ParseMode.HTML)

    def button_callback(self, update: Update, context: CallbackContext):
        data = update.callback_query.data

        if not data.startswith(self.name):
            return

        data_list = data.split("|")

        if not data_list:
            return

        if len(data_list) != 3:
            return

        if int(data_list[1]) != update.effective_user.id:
            return

        message = update.callback_query.message

        key_contract = self.config.get("key_contract")
        neb_contract = self.config.get("neb_contract")
        neb_amount = self.config.get("neb_amount")

        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet)

        action = data_list[2]

        # --- STAKE ---
        if action == self.STAKE:
            message.edit_caption(f"{emo.HOURGLASS} Staking NEB...")

            try:
                # Check if contract is approved to spend NEB
                approved = lamden.get_approved_amount(key_contract, token=neb_contract)
                approved = approved["value"] if "value" in approved else 0
                approved = approved if approved is not None else 0

                msg = f"Approved amount of NEB for {key_contract}: {approved}"
                logging.info(msg)

                if neb_amount > float(approved):
                    app = lamden.approve_contract(key_contract, token=neb_contract)
                    msg = f"Approved {key_contract}: {app}"
                    logging.info(msg)
            except Exception as e:
                logging.error(f"Error approving nebkey contract: {e}")
                message.edit_caption(f"{emo.ERROR} {e}")
                return

            try:
                # Call contract
                key = lamden.post_transaction(
                    stamps=90,
                    contract=key_contract,
                    function="stake",
                    kwargs={}
                )
            except Exception as e:
                logging.error(f"Error calling nebkey contract: {e}")
                message.edit_caption(f"{emo.ERROR} {e}")
                return

            logging.info(f"Executed nebkey contract: {key}")

            if "error" in key:
                logging.error(f"Nebkey contract returned error: {key['error']}")
                message.edit_caption(f"{emo.ERROR} {key['error']}")
                return

            # Get transaction hash
            tx_hash = key["hash"]

            # Wait for transaction to be completed
            success, result = lamden.tx_succeeded(tx_hash)

            if not success:
                logging.error(f"Nebkey transaction not successful: {result}")
                message.edit_caption(f"{emo.ERROR} {result}")
                return

            ex_link = f'<a href="{lamden.explorer_url}/transactions/{tx_hash}">View Transaction on Explorer</a>'

            message.edit_caption(
                f"{result}\n{ex_link}",
                parse_mode=ParseMode.HTML)

            msg = f"NEB staked"
            context.bot.answer_callback_query(update.callback_query.id, msg)

        # --- UNSTAKE ---
        elif action == self.UNSTAKE:
            message.edit_caption(f"{emo.HOURGLASS} Unstaking NEB...")

            try:
                # Call contract
                key = lamden.post_transaction(
                    stamps=90,
                    contract=key_contract,
                    function="unstake",
                    kwargs={}
                )
            except Exception as e:
                logging.error(f"Error calling nebkey contract: {e}")
                message.edit_caption(f"{emo.ERROR} {e}")
                return

            logging.info(f"Executed nebkey contract: {key}")

            if "error" in key:
                logging.error(f"Nebkey contract returned error: {key['error']}")
                message.edit_caption(f"{emo.ERROR} {key['error']}")
                return

            # Get transaction hash
            tx_hash = key["hash"]

            # Wait for transaction to be completed
            success, result = lamden.tx_succeeded(tx_hash)

            if not success:
                logging.error(f"Nebkey transaction not successful: {result}")
                message.edit_caption(f"{emo.ERROR} {result}")
                return

            ex_link = f'<a href="{lamden.explorer_url}/transactions/{tx_hash}">View Transaction on Explorer</a>'

            message.edit_caption(
                f"{result}\n{ex_link}",
                parse_mode=ParseMode.HTML)

            msg = f"NEB unstaked"
            context.bot.answer_callback_query(update.callback_query.id, msg)

    def get_stake_button(self, user_id):
        menu = utl.build_menu([
            InlineKeyboardButton("Stake 1 million NEB", callback_data=f"{self.name}|{user_id}|{self.STAKE}")
        ])
        return InlineKeyboardMarkup(menu, resize_keyboard=True)

    def get_unstake_button(self, user_id):
        menu = utl.build_menu([
            InlineKeyboardButton("Unstake 1 million NEB", callback_data=f"{self.name}|{user_id}|{self.UNSTAKE}")
        ])
        return InlineKeyboardMarkup(menu, resize_keyboard=True)
