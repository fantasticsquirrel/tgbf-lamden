import decimal
import time
import logging
import requests

from typing import Union
from contracting.db.encoder import decode
from lamden.crypto.transaction import build_transaction
from lamden.crypto.wallet import Wallet


class API:

    def __init__(
            self,
            node_host: str = None,
            node_port: int = None,
            wallet: Wallet = None,
            explorer_host: str = None,
            explorer_port: int = None,
            lns: str = None):

        self.node_host = node_host
        self.node_port = node_port
        self.wallet = wallet
        self.explorer_host = explorer_host
        self.explorer_port = explorer_port
        self.lns = lns
        self._node_url = None
        self._explorer_url = None
        self._lns = None

    @property
    def node_url(self):
        """ Get currently set node URL """
        if self.node_port:
            self._node_url = f"{self.node_host}:{self.node_port}"
        else:
            self._node_url = self.node_host

        return self._node_url

    @property
    def explorer_url(self):
        """ Get currently set block explorer URL """
        if self.explorer_port:
            self._explorer_url = f"{self.explorer_host}:{self.explorer_port}"
        else:
            self._explorer_url = self.explorer_host

        return self._explorer_url

    @property
    def lns_url(self):
        if self.lns:
            self._lns = f"{self.lns}"
        else:
            self._lns = self.lns

        return self._lns

    def is_address_valid(self, address: str):
        """ Check if the given address is valid """
        if not len(address) == 64:
            return False
        try:
            int(address, 16)
        except:
            return False
        return True

    # ---- Masternode API ----

    def get_nonce(self, address: str):
        """ Get nonce to use for next transaction """
        with requests.get(f"{self.node_url}/nonce/{address}") as res:
            return decode(res.text)

    def get_latest_block(self):
        """ Get block details for the latest block """
        with requests.get(f"{self.node_url}/latest_block") as res:
            return decode(res.text)

    def get_latest_block_number(self):
        """ Get block number of the latest block """
        with requests.get(f"{self.node_url}/latest_block_num") as res:
            return decode(res.text)

    def get_latest_block_hash(self):
        """ Get the hash of the latest block """
        with requests.get(f"{self.node_url}/latest_block_hash") as res:
            return decode(res.text)

    def get_block_details(self, block_number: Union[int, str]):
        """ Get block details for a given block number """
        with requests.get(f"{self.node_url}/blocks?num={block_number}") as res:
            return decode(res.text)

    def get_balance(self, token: str = "currency", address: str = None, contract: str = None):
        """ Get balance for a given address or for the current
        address if no address is provided as an argument """
        if address and contract:
            key = f"{address}:{contract}"
        elif contract:
            key = contract
        else:
            if address:
                key = address
            else:
                key = self.wallet.verifying_key

        with requests.get(f"{self.node_url}/contracts/{token}/balances?key={key}") as res:
            return decode(res.text)

    def get_contracts(self):
        """ Get all available smart contracts """
        with requests.get(f"{self.node_url}/contracts") as res:
            return decode(res.text)

    def get_transaction_details(self, tx_hash: str):
        """ Get transaction details for given tx hash """
        with requests.get(f"{self.node_url}/tx?hash={tx_hash}") as res:
            return decode(res.text)

    def tx_succeeded(self, tx_hash: str, check_period: float = 3, timeout: float = 60):
        end = int(time.time()) + timeout

        while int(time.time()) < end:
            time.sleep(check_period)

            tx = self.get_transaction_details(tx_hash)
            if "error" in tx:
                if tx["error"] == "Transaction not found.":
                    continue
                else:
                    return False, tx["error"]
            if tx["status"] == 0:
                return True, tx
            else:
                return False, tx["result"]
        return False, "Timeout reached"

    def send(self, amount: Union[int, float, str], to_address: str, token: str = "currency"):
        """ Send TAU to given address by triggering 'currency' smart contract """
        kwargs = {"amount": decimal.Decimal(str(amount)), "to": to_address}
        return self.post_transaction(100, token, "transfer", kwargs)

    def post_transaction(self, stamps: int, contract: str, function: str, kwargs: dict):
        """ Post a transaction to the chain and trigger given smart contract """
        nonce = self.get_nonce(self.wallet.verifying_key)

        tx = build_transaction(
            wallet=self.wallet,
            processor=nonce["processor"],
            stamps=stamps,
            nonce=nonce["nonce"],
            contract=contract,
            function=function,
            kwargs=kwargs)

        logging.info(f"TRANSACTION: {tx}")

        with requests.post(self.node_url, data=tx) as res:
            logging.info(f"TRANSACTION({stamps}, {contract}, {function}, {kwargs}) -> {res.text}")
            return decode(res.text)

    def get_network_constitution(self):
        """ Get the constitution of the network """
        with requests.get(f"{self.node_url}/constitution") as res:
            return decode(res.text)

    def get_contract_methods(self, contract: str):
        """ Get methods for a given smart contract """
        with requests.get(f"{self.node_url}/contracts/{contract}/methods") as res:
            return decode(res.text)

    def get_contract_variables(self, contract: str):
        """ Get variables for a given smart contract """
        with requests.get(f"{self.node_url}/contracts/{contract}/variables") as res:
            return decode(res.text)

    def get_contract_variable(self, contract: str, variable: str, key=None):
        """ Get variables for a given smart contract """
        kwargs = {"key": key} if key else None
        with requests.get(f"{self.node_url}/contracts/{contract}/{variable}", kwargs) as res:
            return decode(res.text)

    def approve_contract(self, contract: str, token: str = "currency", amount: float = 900000000000):
        """ Approve smart contract to spend a specific amount of TAU """
        kwargs = {"amount": decimal.Decimal(str(amount)), "to": contract}

        return self.post_transaction(55, token, "approve", kwargs)

    def get_approved_amount(self, contract: str, token: str = "currency", var: str = "balances"):
        """ Get amount of TAU that is approved to be spent by smart contract """
        key = f"{self.wallet.verifying_key}:{contract}"
        with requests.get(f"{self.node_url}/contracts/{token}/{var}?key={key}") as res:
            return decode(res.text)

    def lns_resolve(self, namespace):
        """ Resolve given namespace to an address with Lamden Name Service (LNS) """
        lns_url = self.lns.replace("{namespace}", namespace)
        with requests.get(lns_url) as res:
            return res.json()

    # ---- Block Explorer API ----

    def get_top_wallets(self):
        """ Get top 20 wallets by amount of TAU """
        with requests.get(f"{self.explorer_url}/api/states/topwallets") as res:
            return decode(res.text)
