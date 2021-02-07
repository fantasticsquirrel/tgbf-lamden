import time
import requests

from contracting.db.encoder import encode, decode
from lamden.crypto.canonical import format_dictionary as fd
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

    def post_transaction(self, amount: int, to_address: str):
        nonce = self.get_nonce(self.wallet.verifying_key)

        payload = {
            'contract': "currency",
            'function': "transfer",
            'kwargs': {"amount": amount, "to": to_address},
            'nonce': nonce["nonce"],
            'processor': nonce["processor"],
            'sender': nonce["sender"],
            'stamps_supplied': 100,  # TODO: What to set here?
        }

        tx = {
            'payload': payload,
            'metadata': {
                'signature': self.wallet.sign(encode(fd(payload))),
                'timestamp': int(time.time())
            }
        }

        try:
            # TODO: Make sure that this is async
            res = requests.post(f"{self.node_url}/", data=encode(fd(tx)))
            return decode(res.text)  # TODO: Can be None on error
        except Exception as e:
            print("ERROR:", e)  # TODO: Better error handling

    def get_network_constitution(self):
        res = requests.get(f"{self.node_url}/constitution")
        return res.json()

    def get_contract_methods(self):
        res = requests.get(f"{self.node_url}/contracts/currency/methods")
        return decode(res.text)

    def get_contract_variables(self):
        res = requests.get(f"{self.node_url}/contracts/currency/variables")
        return decode(res.text)
