import tgbf.emoji as emo
import requests
import logging

from decimal import Decimal
from tgbf.plugin import TGBFPlugin
from telegram import ParseMode, Update
from telegram.ext import CommandHandler, CallbackContext
from tgbf.lamden.connect import Connect
from contracting.db.encoder import decode


class Rocketswap(TGBFPlugin):

    lamden = None

    def load(self):
        self.add_handler(CommandHandler(
            self.handle,
            self.rocketswap_callback,
            run_async=True))

        self.lamden = Connect()

    @TGBFPlugin.send_typing
    def rocketswap_callback(self, update: Update, context: CallbackContext):
        if len(context.args) != 1:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        contract = context.args[0]
        url = self.config.get("price_url")
        url = f"{self.lamden.node_url}{url}{contract}"

        try:
            res = requests.get(url)
        except Exception as e:
            logging.error(f"{emo.ERROR} Can not retrieve price for {contract}: {e}")
            update.message.reply_text(f"{emo.ERROR} {e}")
            self.notify(e)
            return

        price = decode(res.text)

        if "error" in price:
            msg = f"{emo.ERROR} {price['error']}"
            update.message.reply_text(msg)
            return

        price = decode(res.text)["value"]

        if not price:
            msg = f"{emo.ERROR} Not available on Rocketswap"
            update.message.reply_text(msg)
            return

        price = Decimal(str(price))
        price = price.quantize(Decimal(10) ** -8)

        update.message.reply_text(
            text=f"`Price of {contract}\n\n{price} TAU`",
            parse_mode=ParseMode.MARKDOWN_V2)
