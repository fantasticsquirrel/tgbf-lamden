import logging
import requests
import tgbf.emoji as emo

from telegram import Update, ParseMode
from telegram.ext import CommandHandler, CallbackContext
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Lns(TGBFPlugin):

    AVATAR_DIR = "avatars"

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.lns_callback,
            run_async=True))

    @TGBFPlugin.send_typing
    def lns_callback(self, update: Update, context: CallbackContext):
        if len(context.args) < 1:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet)

        command = context.args[0].lower()
        contract = self.config.get("contract")

        # MINT NEW NAMESPACE
        if command == "mint":
            if len(context.args) != 2:
                update.message.reply_text(
                    self.get_usage(),
                    parse_mode=ParseMode.MARKDOWN)
                return

            namespace = context.args[1]

            msg = f"{emo.HOURGLASS} Minting namespace..."
            message = update.message.reply_text(msg)

            try:
                approved = lamden.get_approved_amount(contract)
                approved = approved["value"] if "value" in approved else 0
                approved = approved if approved is not None else 0

                msg = f"Approved amount of TAU for {contract}: {approved}"
                logging.info(msg)

                if 1 > float(approved):
                    app = lamden.approve_contract(contract)
                    msg = f"Approved {contract}: {app}"
                    logging.info(msg)

                mint = lamden.post_transaction(
                    stamps=80,
                    contract=contract,
                    function="mint_nft",
                    kwargs={"name": namespace})

            except Exception as e:
                logging.error(f"Error calling LNS mint contract: {e}")
                msg = f"{emo.ERROR} {e}"
                message.edit_text(msg)
                return

            if "error" in mint:
                logging.error(f"LNS contract returned error: {mint['error']}")
                msg = f"{emo.ERROR} {mint['error']}"
                message.edit_text(msg)
                return

            tx_hash = mint["hash"]

            success, result = lamden.tx_succeeded(tx_hash)

            if not success:
                logging.error(f"Transaction not successful: {result}")
                msg = f"{emo.ERROR} {result}"
                message.edit_text(msg)
                return

            ex_url = f"{lamden.explorer_url}/transactions/{tx_hash}"
            done_msg = f'{emo.DONE} Namespace minted! <a href="{ex_url}">View Tx</a>'

            message.edit_text(
                f"{done_msg}",
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True)
            return

        # LIST NAMESPACES
        elif command == "list":
            address = str()

            if len(context.args) == 2:
                address = context.args[1]

            if not address:
                address = wallet.verifying_key

            if not lamden.is_address_valid(address):
                msg = f"{emo.ERROR} Provided address not valid..."
                update.message.reply_text(msg)
                return

            msg = f"{emo.HOURGLASS} Retrieving namespaces..."
            message = update.message.reply_text(msg)

            try:
                blockservice = self.config.get("blockservice").replace("{address}", address)

                with requests.get(blockservice) as namespaces:
                    namespaces = namespaces.json()

                    if not namespaces:
                        message.edit_text("No namespaces minted yet")
                        return

                    owned_str = str()
                    for name, qty in namespaces[contract]['collection_balances'][address].items():
                        if qty != 1:
                            continue

                        owned_str += f"<code>{name}</code>, "

                    if owned_str:
                        owned_str = owned_str[:-2]

                    message.edit_text(owned_str, parse_mode=ParseMode.HTML)
                    return

            except Exception as e:
                logging.error(f"Not possible to retrieve LNS namespaces for {wallet}: {e}")
                msg = f"{emo.ERROR} {e}"
                message.edit_text(msg)
                return

        # TRANSFER NAMESPACE
        elif command == "transfer":
            if len(context.args) != 3:
                update.message.reply_text(
                    self.get_usage(),
                    parse_mode=ParseMode.MARKDOWN)
                return

            namespace = context.args[1].lower()
            to = context.args[2]

            if not lamden.is_address_valid(to):
                lns_res = lamden.lns_resolve(to)

                if lns_res['status'] == "error":
                    msg = f"{emo.ERROR} Not a valid address or LNS namespace"
                    update.message.reply_text(msg)
                    return

                to = lns_res["response"]

                if not lamden.is_address_valid(to):
                    msg = f"{emo.ERROR} LNS namespace is not a valid address!"
                    update.message.reply_text(msg)
                    return

            msg = f"{emo.HOURGLASS} Transfering namespace..."
            message = update.message.reply_text(msg)

            try:
                transfer = lamden.post_transaction(
                    stamps=80,
                    contract=contract,
                    function="transfer",
                    kwargs={"name": namespace, "amount": 1, "to": to})

            except Exception as e:
                logging.error(f"Error calling LNS transfer contract: {e}")
                msg = f"{emo.ERROR} {e}"
                message.edit_text(msg)
                return

            if "error" in transfer:
                logging.error(f"LNS transfer contract returned error: {transfer['error']}")
                msg = f"{emo.ERROR} {transfer['error']}"
                message.edit_text(msg)
                return

            tx_hash = transfer["hash"]

            # Wait for transaction to be completed
            success, result = lamden.tx_succeeded(tx_hash)

            if not success:
                logging.error(f"Transaction not successful: {result}")
                msg = f"{emo.ERROR} {result}"
                message.edit_text(msg)
                return

            ex_url = f"{lamden.explorer_url}/transactions/{tx_hash}"
            done_msg = f'{emo.DONE} Namespace transfered! <a href="{ex_url}">View Tx</a>'

            message.edit_text(
                f"{done_msg}",
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True)
            return

        # RESOLVE NAMESPACE
        elif command == "resolve":
            if len(context.args) != 2:
                update.message.reply_text(
                    self.get_usage(),
                    parse_mode=ParseMode.MARKDOWN)
                return

            namespace = context.args[1].lower()

            msg = f"{emo.HOURGLASS} Resolving namespace..."
            message = update.message.reply_text(msg)

            try:
                response = lamden.lns_resolve(namespace)

                if "status" not in response:
                    message.edit_text(f"{emo.ERROR} Can not resolve namespace")
                    return
                if response["status"] == "error":
                    message.edit_text(f"{emo.ERROR} {response['response']}")
                    return

                message.edit_text(f"<code>{response['response']}</code>", parse_mode=ParseMode.HTML)
                return

            except Exception as e:
                logging.error(f"Resolver returned error: {e}")
                msg = f"{emo.ERROR} {e}"
                message.edit_text(msg)
                return

        # COUNT NAMESPACES
        elif command == "count":
            msg = f"{emo.HOURGLASS} Counting namespaces..."
            message = update.message.reply_text(msg)

            try:
                blockservice = self.config.get("blockservice").replace("{address}", "")

                with requests.get(blockservice) as namespaces:
                    namespaces = namespaces.json()

                    counter = 0
                    for address, namespace_dict in namespaces[contract]['collection_balances'].items():
                        counter += sum(x == 1 for x in namespace_dict.values())

                    message.edit_text(f'<code>{counter}</code> LNS namespaces generated', parse_mode=ParseMode.HTML)
                    return

            except Exception as e:
                logging.error(f"Not possible to retrieve LNS namespaces for {wallet}: {e}")
                msg = f"{emo.ERROR} {e}"
                message.edit_text(msg)
                return

        elif command == "avatar":
            if len(context.args) != 2:
                update.message.reply_text(
                    self.get_usage(),
                    parse_mode=ParseMode.MARKDOWN)
                return

            msg = f"{emo.HOURGLASS} Retrieving avatar..."
            message = update.message.reply_text(msg)

            namespace = context.args[1].lower()

            try:
                blockservice = self.config.get("blockservice") \
                    .replace("collection_balances", "collection_nfts")\
                    .replace("{address}", "")

                with requests.get(blockservice) as bs:
                    bs = bs.json()

                    if namespace not in bs[contract]['collection_nfts']:
                        msg = f'{emo.ERROR} LNS namespace does not exist'
                        message.edit_text(msg)
                        return

                    message.delete()
                    update.message.reply_photo(
                        photo=f"https://robohash.org/{namespace}?set=set4",
                        caption=f"Avatar for namespace <code>{namespace}</code>",
                        parse_mode=ParseMode.HTML)
                    return

            except Exception as e:
                logging.error(f"Not possible to retrieve LNS namespaces for {wallet}: {e}")
                msg = f"{emo.ERROR} {e}"
                message.edit_text(msg)
                return

        else:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return
