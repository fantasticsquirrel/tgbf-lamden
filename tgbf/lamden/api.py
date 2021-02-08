from typing import Union

import requests

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
        self._node_url = self.host if self.port is None else f"{self.host}:{self.port}"
        return self._node_url

    def is_address_valid(self, address: str):
        if not len(address) == 64:
            return False
        if not address.isalnum():
            return False
        return True

    def get_nonce(self, address):
        res = requests.get(f"{self.node_url}/nonce/{address}")
        return decode(res.text)

    def get_latest_block(self):
        res = requests.get(f"{self.node_url}/latest_block")
        return decode(res.text)

    def get_latest_block_number(self):
        res = requests.get(f"{self.node_url}/latest_block_num")
        return decode(res.text)

    def get_latest_block_hash(self):
        res = requests.get(f"{self.node_url}/latest_block_hash")
        return decode(res.text)

    def get_block_details(self, block_number):
        res = requests.get(f"{self.node_url}/blocks?num={block_number}")
        return decode(res.text)

    def get_balance(self, address):
        res = requests.get(f"{self.node_url}/contracts/currency/balances?key={address}")
        return decode(res.text)

    def get_contracts(self):
        res = requests.get(f"{self.node_url}/contracts")
        return decode(res.text)

    def get_transaction_details(self, tx_hash):
        res = requests.get(f"{self.node_url}/tx?hash={tx_hash}")
        return decode(res.text)

    def post_transaction(self, amount: Union[int, float], to_address: str):
        nonce = self.get_nonce(self.wallet.verifying_key)

        tx = build_transaction(
            wallet=self.wallet,
            processor=nonce["processor"],
            stamps=100,
            nonce=nonce["nonce"],
            contract="currency",
            function="transfer",
            kwargs={"amount": amount, "to": to_address}
        )

        res = requests.post(self.node_url, data=tx)
        return decode(res.text)

    def get_network_constitution(self):
        res = requests.get(f"{self.node_url}/constitution")
        return decode(res.text)

    def get_contract_methods(self):
        res = requests.get(f"{self.node_url}/contracts/currency/methods")
        return decode(res.text)

    def get_contract_variables(self):
        res = requests.get(f"{self.node_url}/contracts/currency/variables")
        return decode(res.text)
