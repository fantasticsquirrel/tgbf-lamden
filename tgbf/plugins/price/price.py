import tgbf.utils as utl
import tgbf.emoji as emo
import logging

from tgbf.plugin import TGBFPlugin
from pycoingecko import CoinGeckoAPI
from telegram import ParseMode, Update
from telegram.ext import CommandHandler, CallbackContext


class Price(TGBFPlugin):

    CGID = "lamden"

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.price_callback,
            run_async=True))

    @TGBFPlugin.blacklist
    @TGBFPlugin.send_typing
    def price_callback(self, update: Update, context: CallbackContext):
        if len(context.args) == 1:
            if context.args[0].lower() == "jeff":
                update.message.reply_text(
                    f"`1 JEFF = 1 JEFF`",
                    parse_mode=ParseMode.MARKDOWN_V2)
                return
            elif context.args[0].lower() == "doug":
                update.message.reply_text(
                    f"`1 DOUG = 1 DOUG`",
                    parse_mode=ParseMode.MARKDOWN_V2)
                return

        try:
            data = CoinGeckoAPI().get_coin_by_id(self.CGID)
        except Exception as e:
            error = f"{emo.ERROR} Could not retrieve price"
            update.message.reply_text(error)
            logging.error(e)
            self.notify(e)
            return

        if not data:
            update.message.reply_text(f"{emo.ERROR} Could not retrieve data")
            return

        name = data["name"]
        symbol = data["symbol"].upper()

        usd = data["market_data"]["current_price"]["usd"]
        eur = data["market_data"]["current_price"]["eur"]
        btc = data["market_data"]["current_price"]["btc"]
        eth = data["market_data"]["current_price"]["eth"]

        p_usd = utl.format(usd, force_length=True)
        p_eur = utl.format(eur, force_length=True, template=p_usd)
        p_btc = utl.format(btc, force_length=True, template=p_usd)
        p_eth = utl.format(eth, force_length=True, template=p_usd)

        p_usd = "{:>12}".format(p_usd)
        p_eur = "{:>12}".format(p_eur)
        p_btc = "{:>12}".format(p_btc)
        p_eth = "{:>12}".format(p_eth)

        msg = f"{name} ({symbol})\n\n" \
              f"USD {p_usd}\n" \
              f"EUR {p_eur}\n" \
              f"BTC {p_btc}\n" \
              f"ETH {p_eth}\n\n"

        update.message.reply_text(
            text=f"`{msg}`",
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True,
            quote=False)
