import tgbf.emoji as emo

from telegram import Update
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

    @TGBFPlugin.private
    @TGBFPlugin.send_typing
    def balance_callback(self, update: Update, context: CallbackContext):
        msg = f"{emo.HOURGLASS} Retrieving token balances..."
        message = update.message.reply_text(msg)

        wallet = self.get_wallet(update.effective_user.id)
        lamden = Connect(wallet=wallet)

        # Find longest token symbol
        max_length = max([len(t[0]) for t in lamden.tokens if len(t[0])])

        balances = str()
        for token in lamden.tokens:
            b = lamden.get_balance(token[1])
            b = b["value"] if "value" in b else 0
            b = float(str(b)) if b else float("0")

            # There is a balance for this token
            if b > 0:
                t_symbol = f"{token[0]}:"
                b = f"{int(b):,}" if b.is_integer() else f"{b:,.2f}"
                balances += f"{t_symbol:<{max_length + 1}} {b}\n"

        message.edit_text(
            text=f"<code>{balances}</code>",
            parse_mode=ParseMode.HTML
        )
