import time
import math
import requests

from tgbf.lamden.wallet import LamdenWallet
from contracting.db.encoder import encode, decode
#from lamden.crypto.canonical import format_dictionary


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

    def get_balance(self, address, raw=True):
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

    def post_transaction(self, from_wallet: LamdenWallet, amount: int, to_address: str):
        def format_dictionary(d: dict) -> dict:
            for k, v in d.items():
                assert type(k) == str, 'Non-string key types not allowed.'
                if type(v) == list:
                    for i in range(len(v)):
                        if isinstance(v[i], dict):
                            v[i] = format_dictionary(v[i])
                elif isinstance(v, dict):
                    d[k] = format_dictionary(v)
            return {k: v for k, v in sorted(d.items())}

        nonce = self.get_nonce(from_wallet.address)

        payload = {
            'contract': "currency",
            'function': "transfer",
            'kwargs': {"amount": amount, "to": to_address},
            'nonce': nonce["nonce"],
            'processor': nonce["processor"],
            'sender': nonce["sender"],
            'stamps_supplied': 5000,  # TODO: What to set here?
        }

        # Sort payload in case kwargs unsorted
        payload = format_dictionary(payload)

        true_payload = encode(decode(encode(payload)))

        metadata = {
            'signature': from_wallet.sign(true_payload),
            'timestamp': int(time.time())
        }

        tx = {
            'payload': payload,
            'metadata': metadata
        }

        encoded_payload = encode(format_dictionary(tx))

        try:
            # TODO: Make sure that this is async
            res = requests.post(f"{self.node_url}/", data=encoded_payload)
            print(res)
        except Exception as e:
            print("ERROR:", e)

    def get_network_constitution(self):
        res = requests.get(f"{self.node_url}/constitution")
        return res.json()

    def get_contract_methods(self):
        res = requests.get(f"{self.node_url}/contracts/currency/methods")
        return res.json()

    def get_contract_variables(self):
        res = requests.get(f"{self.node_url}/contracts/currency/variables")
        return res.json()
