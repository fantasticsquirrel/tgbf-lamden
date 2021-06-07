import tgbf.emoji as emo
import requests
import logging

from decimal import Decimal
from tgbf.plugin import TGBFPlugin
from pycoingecko import CoinGeckoAPI
from telegram import ParseMode, Update
from telegram.ext import CommandHandler, CallbackContext
from tgbf.lamden.connect import Connect
from contracting.db.encoder import decode


class Rsprice(TGBFPlugin):

    CGID = "lamden"
    VS_CUR = "usd,eur"

    DECIMALS = 8

    def load(self):
        self.add_handler(CommandHandler(
            self.handle,
            self.rsprice,
            run_async=True))

    @TGBFPlugin.blacklist
    @TGBFPlugin.send_typing
    def rsprice(self, update: Update, context: CallbackContext):
        if len(context.args) != 1:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        token_symbol = context.args[0].upper()

        lamden = Connect()

        sql = self.get_resource("select_contract.sql", plugin="tokens")
        res = self.execute_sql(sql, token_symbol, plugin="tokens")

        if res and res["data"] and res["data"][0]:
            contract = res["data"][0][0]
        else:
            msg = f"{emo.ERROR} Unknown token"
            update.message.reply_text(msg)
            return

        url = self.config.get("price_url")
        url = f"{lamden.node_url}{url}{contract}"

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
        price = price.quantize(Decimal(10) ** - self.DECIMALS)

        rs_url = f"https://rocketswap.exchange/#/{contract}"
        msg = f"[Trade on Rocketswap]({rs_url})\n\n`TAU: {price}`\n"

        message = update.message.reply_text(
            text=msg,
            parse_mode=ParseMode.MARKDOWN_V2)

        try:
            data = CoinGeckoAPI().get_coin_by_id(self.CGID)
            prices = data["market_data"]["current_price"]

            value = str()

            for c in self.VS_CUR.split(","):
                if c in prices:
                    p = f'{(prices[c] * float(price)):.{self.DECIMALS}f}'
                    value += f"{c.upper()}: {p}\n"

            msg += f"`" \
                   f"{value}" \
                   f"`"

            message.edit_text(
                text=msg,
                parse_mode=ParseMode.MARKDOWN_V2)
        except Exception as e:
            logging.warning(f"Could not calculate value for user balance: {e}")

