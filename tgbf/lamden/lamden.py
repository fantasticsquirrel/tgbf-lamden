import requests

from tgbf.lamden.wallet import LamdenWallet
from contracting.client import ContractingClient


class Lamden:

    def __init__(self, host: str = None, port: int = None, wallet: LamdenWallet = None):
        self.host = host
        self.port = port
        self.wallet = wallet
        self._node_url = None

        # Make sure mongodb instance is running
        # https://blog.lamden.io/smart-contracting-with-python-2af233620dca
        self.client = ContractingClient()

    @property
    def node_url(self):
        self._node_url = self.host if self.port is None else f"{self.host}:{self.port}"
        return self._node_url

    def get_nonce(self, address):
        res = requests.get(f"{self.node_url}/nonce/{address}")
        return res.json()["nonce"]

    def get_latest_block(self):
        res = requests.get(f"{self.node_url}/latest_block")
        return res.json()

    def get_latest_block_number(self):
        res = requests.get(f"{self.node_url}/latest_block_num")
        return res.json()["latest_block_number"]

    def get_balance(self, address):
        res = requests.get(f"{self.node_url}/contracts/currency/balances?key={address}")
        balance = res.json()["value"]
        return "0" if balance is None else balance["__fixed__"]

    def get_contracts(self):
        res = requests.get(f"{self.node_url}/contracts")
        return res.json()
