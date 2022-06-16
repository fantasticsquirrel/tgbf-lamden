import uuid
import decimal
import logging
import requests
import tgbf.emoji as emo
import tgbf.utils as utl

from contracting.db.encoder import decode
from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from tgbf.lamden.connect import Connect
from tgbf.plugin import TGBFPlugin


class Lns(TGBFPlugin):

    AVATAR_DIR = "avatars"

    tmp_market = dict()

    def load(self):
        self.add_handler(CommandHandler(
            self.name,
            self.lns_callback,
            run_async=True))

        self.add_handler(CallbackQueryHandler(
            self.button_callback,
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

            blockservice = self.config.get("blockservice") + f"current/all/{contract}/collection_balances/{address}"

            try:
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

            blockservice = self.config.get("blockservice") + f"current/all/{contract}/collection_balances"

            try:
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

        # SHOW NAMESPACE AVATAR
        elif command == "avatar":
            if len(context.args) != 2:
                update.message.reply_text(
                    self.get_usage(),
                    parse_mode=ParseMode.MARKDOWN)
                return

            msg = f"{emo.HOURGLASS} Retrieving avatar..."
            message = update.message.reply_text(msg)

            namespace = context.args[1].lower()

            blockservice = self.config.get("blockservice") + f"current/all/{contract}/collection_nfts"

            try:
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

        # SELL NAMESPACE
        elif command == "sell":
            if len(context.args) < 3:
                update.message.reply_text(
                    self.get_usage(),
                    parse_mode=ParseMode.MARKDOWN)
                return

            namespace = context.args[1].lower()
            price = context.args[2]

            nft_market = self.config.get("nft_market_contract")

            msg = f"{emo.HOURGLASS} Listing NFT for sale..."
            message = update.message.reply_text(msg)

            try:
                approval = "collection_balances_approvals"
                key = f"{wallet.verifying_key}:{nft_market}:{namespace}"
                with requests.get(f"{lamden.node_url}/contracts/{contract}/{approval}?key={key}") as res:
                    approved = decode(res.text)
                    approved = approved["value"] if "value" in approved else 0
                    approved = approved if approved is not None else 0

                msg = f"Approved amount of {nft_market} for {contract}: {approved}"
                logging.info(msg)

                if 1 > float(approved):
                    lamden.post_transaction(
                        stamps=100,
                        contract=contract,
                        function="approve",
                        kwargs={
                            "amount": 9999999,
                            "name": namespace,
                            "to": nft_market
                        })

                sell = lamden.post_transaction(
                    stamps=100,
                    contract=nft_market,
                    function="sell_nft",
                    kwargs={
                        "name_of_nft": namespace,
                        "collection_contract": contract,
                        "amount": 1,
                        "currency_price": decimal.Decimal(price)
                    })

            except Exception as e:
                logging.error(f"Error calling NFT marketplace sell contract: {e}")
                msg = f"{emo.ERROR} {e}"
                message.edit_text(msg)
                return

            if "error" in sell:
                logging.error(f"NFT marketplace contract returned error: {sell['error']}")
                msg = f"{emo.ERROR} {sell['error']}"
                message.edit_text(msg)
                return

            tx_hash = sell["hash"]

            success, result = lamden.tx_succeeded(tx_hash)

            if not success:
                logging.error(f"Transaction not successful: {result}")
                msg = f"{emo.ERROR} {result}"
                message.edit_text(msg)
                return

            ex_url = f"{lamden.explorer_url}/transactions/{tx_hash}"
            done_msg = f'{emo.DONE} Namespace <code>{namespace}</code> listed! <a href="{ex_url}">View Tx</a>'

            message.edit_text(
                f"{done_msg}",
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True)
            return

        # BUY NAMESPACE
        elif command == "buy":
            if len(context.args) < 2:
                update.message.reply_text(
                    self.get_usage(),
                    parse_mode=ParseMode.MARKDOWN)
                return

            namespace = context.args[1].lower()

            nft_market = self.config.get("nft_market_contract")
            blockservice = self.config.get("blockservice") + f"current/all/{nft_market}/market"

            msg = f"{emo.HOURGLASS} Checking market..."
            message = update.message.reply_text(msg)

            try:
                with requests.get(blockservice) as m:
                    market = m.json()

                seller, price = self.get_market_data(market, namespace)

                if not seller or not price:
                    msg = f"{emo.ERROR} Namespace <code>{namespace}</code> not available on market"
                    message.edit_text(msg, parse_mode=ParseMode.HTML)
                    return

                current_id = str(uuid.uuid4())
                self.tmp_market[current_id] = {"namespace": namespace, "seller": seller, "price": price}

                message.edit_text(
                    text=f"Namespace <code>{namespace}</code> costs <code>{price}</code> RTAU",
                    reply_markup=self.get_buy_button(current_id),
                    parse_mode=ParseMode.HTML
                )

            except Exception as e:
                logging.error(f"Error calling NFT marketplace buy contract: {e}")
                msg = f"{emo.ERROR} {e}"
                message.edit_text(msg)
                return

        elif command == "cancel":
            if len(context.args) < 2:
                update.message.reply_text(
                    self.get_usage(),
                    parse_mode=ParseMode.MARKDOWN)
                return

            namespace = context.args[1].lower()

            nft_market = self.config.get("nft_market_contract")

            msg = f"{emo.HOURGLASS} Cancel selling namespace..."
            message = update.message.reply_text(msg)

            try:
                cancel = lamden.post_transaction(
                    stamps=100,
                    contract=nft_market,
                    function="refund_nft",
                    kwargs={
                        "name_of_nft": namespace,
                        "collection_contract": contract
                    })

            except Exception as e:
                logging.error(f"Error calling NFT marketplace cancel contract: {e}")
                msg = f"{emo.ERROR} {e}"
                message.edit_text(msg)
                return

            if "error" in cancel:
                logging.error(f"NFT marketplace cancel returned error: {cancel['error']}")
                msg = f"{emo.ERROR} {cancel['error']}"
                message.edit_text(msg)
                return

            tx_hash = cancel["hash"]

            success, result = lamden.tx_succeeded(tx_hash)

            if not success:
                logging.error(f"Transaction not successful: {result}")
                msg = f"{emo.ERROR} {result}"
                message.edit_text(msg)
                return

            ex_url = f"{lamden.explorer_url}/transactions/{tx_hash}"
            done_msg = f'{emo.DONE} Selling Namespace <code>{namespace}</code> canceled! <a href="{ex_url}">View Tx</a>'

            message.edit_text(
                f"{done_msg}",
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True)
            return

        # EVERYTHING ELSE
        else:
            update.message.reply_text(
                self.get_usage(),
                parse_mode=ParseMode.MARKDOWN)
            return

    def button_callback(self, update: Update, context: CallbackContext):
        message = update.callback_query.message
        data = update.callback_query.data

        if not data.startswith(self.name):
            return

        data_list = data.split("|")

        if not data_list:
            return

        offer_id = data_list[1]

        namespace = self.tmp_market[offer_id]["namespace"]
        seller = self.tmp_market[offer_id]["seller"]

        lns = self.config.get("contract")
        rtau = self.config.get("rtau_contract")
        rtau_treasury = self.config.get("rtau_treasury_contract")
        nft_market = self.config.get("nft_market_contract")

        usr_id = update.effective_user.id
        wallet = self.get_wallet(usr_id)
        lamden = Connect(wallet)

        try:
            # Approve RTAU --> NFT Markerplace
            approved = lamden.get_approved_amount(nft_market, token=rtau)
            approved = approved["value"] if "value" in approved else 0
            approved = approved if approved is not None else 0

            msg = f"Approved amount of {nft_market} for {rtau}: {approved}"
            logging.info(msg)

            if 1 > float(approved):
                app = lamden.approve_contract(nft_market, token=rtau)
                msg = f"Approved {rtau}: {app}"
                logging.info(msg)

            # Approve RTAU --> RTAU Treasury
            approved = lamden.get_approved_amount(rtau_treasury, token=rtau)
            approved = approved["value"] if "value" in approved else 0
            approved = approved if approved is not None else 0

            msg = f"Approved amount of {rtau_treasury} for {rtau}: {approved}"
            logging.info(msg)

            if 1 > float(approved):
                app = lamden.approve_contract(rtau_treasury, token=rtau)
                msg = f"Approved {rtau}: {app}"
                logging.info(msg)

            sell = lamden.post_transaction(
                stamps=200,
                contract=nft_market,
                function="buy_nft",
                kwargs={
                    "name": namespace,
                    "collection_contract": lns,
                    "seller": seller,
                    "amount": 1
                })

            self.tmp_market.pop(offer_id, None)
            update.callback_query.message.edit_text(f"{emo.HOURGLASS} Buying namespace...")

        except Exception as e:
            logging.error(f"Error calling NFT marketplace buy contract: {e}")
            message.edit_text(f"{emo.ERROR} {e}")
            return

        if "error" in sell:
            logging.error(f"NFT marketplace buy returned error: {sell['error']}")
            message.edit_text(f"{emo.ERROR} {sell['error']}")
            return

        tx_hash = sell["hash"]

        success, result = lamden.tx_succeeded(tx_hash)

        if not success:
            logging.error(f"Transaction not successful: {result}")
            message.edit_text(f"{emo.ERROR} {result}")
            return

        ex_url = f"{lamden.explorer_url}/transactions/{tx_hash}"
        done_msg = f'{emo.DONE} Namespace <code>{namespace}</code> bought! <a href="{ex_url}">View Tx</a>'

        message.edit_text(
            f"{done_msg}",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True)

    def get_market_data(self, market, namespace):
        market = market["con_nft_marketplace_v1"]["market"]
        contract = self.config.get("contract")

        for seller, nft_contract_dict in market.items():
            for nft_contract, nft_contract_detail_dict in nft_contract_dict.items():
                if nft_contract != contract:
                    continue
                for name, details_dict in nft_contract_detail_dict.items():
                    if name == namespace and details_dict["amount"] == 1:
                        return seller, details_dict["price"]["__fixed__"]

        return None, None

    def get_buy_button(self, offer_id):
        price = self.tmp_market[offer_id]["price"]

        menu = utl.build_menu([
            InlineKeyboardButton(
                f"Buy for {int(price)} RTAU", callback_data=f"{self.name}|{offer_id}")
        ])
        return InlineKeyboardMarkup(menu, resize_keyboard=True)
