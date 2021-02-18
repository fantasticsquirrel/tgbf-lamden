import time
import requests

from typing import Union
from contracting.db.encoder import decode
from lamden.crypto.transaction import build_transaction
from lamden.crypto.wallet import Wallet


class API:

    def __init__(self, host: str = None, port: int = None, wallet: Wallet = None):
        self.host = host
        self.port = port
        self.wallet = wallet
        self._node_url = None

    @property
    def node_url(self):
        """ Get currently set node URL """
        self._node_url = self.host if self.port is None else f"{self.host}:{self.port}"
        return self._node_url

    def is_address_valid(self, address: str):
        """ Check if the given address is valid """
        if not len(address) == 64:
            return False
        try:
            int(address, 16)
        except:
            return False
        return True

    def get_nonce(self, address):
        """ Get nonce to use for next transaction """
        res = requests.get(f"{self.node_url}/nonce/{address}")
        return decode(res.text)

    def get_latest_block(self):
        """ Get block details for the latest block """
        res = requests.get(f"{self.node_url}/latest_block")
        return decode(res.text)

    def get_latest_block_number(self):
        """ Get block number of the latest block """
        res = requests.get(f"{self.node_url}/latest_block_num")
        return decode(res.text)

    def get_latest_block_hash(self):
        """ Get the hash of the latest block """
        res = requests.get(f"{self.node_url}/latest_block_hash")
        return decode(res.text)

    def get_block_details(self, block_number):
        """ Get block details for a given block number """
        res = requests.get(f"{self.node_url}/blocks?num={block_number}")
        return decode(res.text)

    def get_balance(self, address):
        """ Get balance for a given address """
        res = requests.get(f"{self.node_url}/contracts/currency/balances?key={address}")
        return decode(res.text)

    def get_contracts(self):
        """ Get all available smart contracts """
        res = requests.get(f"{self.node_url}/contracts")
        return decode(res.text)

    def get_transaction_details(self, tx_hash):
        """ Get transaction details for given tx hash """
        res = requests.get(f"{self.node_url}/tx?hash={tx_hash}")
        return decode(res.text)

    def tx_successful(self, tx_hash, check_period=0.5, timeout=5):
        end = int(time.time()) + timeout

        while int(time.time()) < end:
            time.sleep(check_period)

            tx = self.get_transaction_details(tx_hash)
            if "error" in tx:
                if tx["error"] == "Transaction not found.":
                    continue
                else:
                    return False, tx
            else:
                return True, tx
        return False, {"error": "Timeout reached"}

    def send(self, amount: Union[int, float], to_address: str):
        """ Send TAU to given address by triggering 'currency' smart contract """
        kwargs = {"amount": amount, "to": to_address}
        return self.post_transaction(100, "currency", "transfer", kwargs)

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

        res = requests.post(self.node_url, data=tx)
        return decode(res.text)

    def get_network_constitution(self):
        """ Get the constitution of the network """
        res = requests.get(f"{self.node_url}/constitution")
        return decode(res.text)

    def get_contract_methods(self, contract):
        """ Get methods for a given smart contract """
        res = requests.get(f"{self.node_url}/contracts/{contract}/methods")
        return decode(res.text)

    def get_contract_variables(self, contract):
        """ Get variables for a given smart contract """
        res = requests.get(f"{self.node_url}/contracts/{contract}/variables")
        return decode(res.text)

    def approve_contract(self, contract_name, amount: float = 100000000):
        """ Approve smart contract to spend a specific amount of TAU """
        kwargs = {"amount": float(amount), "to": contract_name}
        return self.post_transaction(500, "currency", "approve", kwargs)

    def get_approved_amount(self, contract_name):
        """ Get amount of TAU that is approved to be spent by smart contract """
        key = f"{self.wallet.verifying_key}:{contract_name}"
        res = requests.get(f"{self.node_url}/contracts/currency/balances?key={key}")
        return decode(res.text)
