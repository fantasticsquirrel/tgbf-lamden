import time
import math
import json
import requests

from tgbf.lamden.wallet import LamdenWallet


class Lamden:

    def __init__(self, host: str = None, port: int = None, wallet: LamdenWallet = None):
        self.host = host
        self.port = port
        self.wallet = wallet
        self._node_url = None

    @property
    def node_url(self):
        self._node_url = self.host if self.port is None else f"{self.host}:{self.port}"
        return self._node_url

    def get_nonce(self, address, raw=True):
        res = requests.get(f"{self.node_url}/nonce/{address}")
        return res.json() if raw else res.json()["nonce"]

    def get_latest_block(self):
        res = requests.get(f"{self.node_url}/latest_block")
        return res.json()

    def get_latest_block_number(self, raw=True):
        res = requests.get(f"{self.node_url}/latest_block_num")
        return res.json() if raw else res.json()["latest_block_number"]

    def get_latest_block_hash(self, raw=True):
        res = requests.get(f"{self.node_url}/latest_block_hash")
        return res.json() if raw else res.json()["latest_block_hash"]

    def get_block_details(self, block_number):
        res = requests.get(f"{self.node_url}/blocks?num={block_number}")
        return res.json()

    def get_balance(self, address, raw=False):
        res = requests.get(f"{self.node_url}/contracts/currency/balances?key={address}")

        if raw:
            return res.json()

        data = res.json()["value"]

        if isinstance(data, dict) and "__fixed__" in data:
            data = data["__fixed__"]

        if data is None:
            return 0

        data = math.floor(float(data) * 100)/100.0
        data = int(data) if data.is_integer() else data

        return data

    def get_contracts(self):
        res = requests.get(f"{self.node_url}/contracts")
        return res.json()

    def get_transaction_details(self, tx_hash):
        res = requests.get(f"{self.node_url}/tx?hash={tx_hash}")
        return res.json()

    def post_transaction(self, wallet: LamdenWallet, amount, to, processor: str, stamps: int):
        def encode(data: str):
            return json.dumps(data, cls=Encoder, separators=(',', ':'))

        def decode(data):
            if data is None:
                return None

            if isinstance(data, bytes):
                data = data.decode()

            try:
                return json.loads(data, parse_float=ContractingDecimal, object_hook=as_object)
            except json.decoder.JSONDecodeError as e:
                return None

        payload = {
            'contract': "currency",
            'function': "transfer",
            'kwargs': {'amount': amount, 'to': to},
            'nonce': self.get_nonce(wallet.address),
            'processor': processor,
            'sender': wallet.address,
            'stamps_supplied': stamps,
        }

        true_payload = encode(decode(encode(payload)))

        metadata = {
            'signature': wallet.sign(true_payload),
            'timestamp': int(time.time())
        }

        tx = {
            'payload': payload,
            'metadata': metadata
        }

        res = requests.post(f"{self.node_url}/{encode(tx)}")

    def get_network_constitution(self):
        res = requests.get(f"{self.node_url}/constitution")
        return res.json()

    def get_contract_methods(self):
        res = requests.get(f"{self.node_url}/contracts/currency/methods")
        return res.json()

    def get_contract_variables(self):
        res = requests.get(f"{self.node_url}/contracts/currency/variables")
        return res.json()
