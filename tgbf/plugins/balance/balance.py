import logging
import tgbf.utils as utl

from telegram import Update
from pycoingecko import CoinGeckoAPI
from tgbf.lamden.connect import Connect
from telegram.ext import CommandHandler, CallbackContext
from telegram import ParseMode
from tgbf.plugin import TGBFPlugin


class Balance(TGBFPlugin):

    CGID = "lamden"
    VS_CUR = "usd,eur"

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.balance_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def balance_callback(self, update: Update, context: CallbackContext):
        wallet = self.get_wallet(update.effective_user.id)
        lamden = Connect(wallet=wallet)

        b = lamden.get_balance(wallet.verifying_key)
        b = b["value"] if "value" in b else 0
        b = str(b) if b else "0"

        b = str(int(b)) if float(b).is_integer() else "{:.2f}".format(float(b))

        message = update.message.reply_text(
            text=f"`TAU: {b}`",
            parse_mode=ParseMode.MARKDOWN_V2
        )

        try:
            data = CoinGeckoAPI().get_coin_by_id(self.CGID)
            prices = data["market_data"]["current_price"]

            value = str()

            for c in self.VS_CUR.split(","):
                if c in prices:
                    price = utl.format(prices[c] * float(b), decimals=2)
                    value += f"{c.upper()}: {price}\n"

            final_msg = f"`" \
                        f"TAU: {b}\n" \
                        f"{value}" \
                        f"`"

            message.edit_text(
                text=final_msg,
                parse_mode=ParseMode.MARKDOWN_V2)
        except Exception as e:
            logging.warning(f"Could not calculate value for user balance: {e}")
