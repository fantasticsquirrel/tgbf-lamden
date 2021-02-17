from contracting.client import ContractingClient
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Dice(TGBFPlugin):

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.dice_callback,
            run_async=True))

    def dice_callback(self, update: Update, context: CallbackContext):
        wallet = self.get_wallet(update.effective_user.id)

        def dice():
            random.seed()

            @export
            def roll():
                return random.randint(1, 6)

        client = ContractingClient()

        client.submit(dice)

        dice = client.get_contract("con_dice")
        result = dice.roll()
        print(result)

        api = Connect(wallet)
        res = api.post_transaction(500, "con_dice", "roll", {})
        print("dice", res)
