from tgbf.plugin import TGBFPlugin
from tgbf.lamden.rocketswap import Rocketswap as rswp
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

        tokens = self.execute_sql(self.get_resource("search_token.sql", plugin="tokens"), query)

        if not tokens["data"]:
            return

        results = list()
        for token in tokens:
            print(token)

            results.append(
                InlineQueryResultArticle(
                    id=query.upper(),
                    title='Caps',
                    input_message_content=InputTextMessageContent(query.upper())
                )
            )

        context.bot.answer_inline_query(update.inline_query.id, results)

        #rswp.token()
