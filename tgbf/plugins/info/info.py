from uuid import uuid4
from tgbf.plugin import TGBFPlugin
from tgbf.lamden.rocketswap import Rocketswap
from telegram import Update, ParseMode, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import CallbackContext, InlineQueryHandler


class Info(TGBFPlugin):

    def load(self):
        self.add_handler(InlineQueryHandler(
            self.send_token_info,
            run_async=True))

    @TGBFPlugin.send_typing
    def send_token_info(self, update: Update, context: CallbackContext):
        query = update.inline_query.query
        if not query:
            return

        sql = self.get_resource("search_tokens.sql", plugin="tokens")
        sql = sql.replace("?", f"'%{query}%'")

        tokens = self.execute_sql(sql, plugin="tokens")

        if not tokens["data"]:
            return

        results = list()
        rs = Rocketswap()

        for token in tokens["data"]:
            details = rs.token(token[0])

            tkn_symbol = details["token"]["token_symbol"]
            tkn_name = details["token"]["token_name"]
            tkn_contract = details["token"]["contract_name"]
            tkn_dev = details["token"]["developer"]
            tkn_logo = details["token"]["token_base64_png"]

            if "lp_info" in details:
                tkn_lp = details["lp_info"]["lp"]
                tkn_price = details["lp_info"]["price"]
                tkn_res_tau = details["lp_info"]["reserves"][0]
                tkn_res_tkn = details["lp_info"]["reserves"][1]

                token_info = f"{tkn_name} ({tkn_symbol})\n" \
                             f"<code>{tkn_contract}</code>\n\n" \
                             f"Price: {round(float(tkn_price), 8)} TAU\n\n" \
                             f"Liquidity Points: {int(float(tkn_lp))}\n" \
                             f"Reserves: {int(float(tkn_res_tau)):,} TAU\n" \
                             f"Reserves: {int(float(tkn_res_tkn)):,} {tkn_symbol}\n"
            else:
                token_info = f"{tkn_name} ({tkn_symbol})\n" \
                             f"Contract: <code>{tkn_contract}</code>\n\n"

            results.append(
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title=f"{token[1]} - {token[0]}",
                    input_message_content=InputTextMessageContent(token_info, parse_mode=ParseMode.HTML)
                )
            )

        context.bot.answer_inline_query(update.inline_query.id, results)
