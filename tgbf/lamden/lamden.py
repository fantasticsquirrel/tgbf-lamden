import logging
import requests

from tgbf.lamden.wallet import LamdenWallet
from contracting.client import ContractingClient


class Lamden:

    def __init__(self, host: str = None, port: int = None, wallet: LamdenWallet = None):
        self.host = host
        self.port = port
        self.wallet = wallet
        self._node_url = None
        self.client = ContractingClient()  # TODO: mongodb wird benötigt - in README rein

    @property
    def node_url(self):
        self._node_url = self.host if self.port is None else f"{self.host}:{self.port}"
        return self._node_url

    def get_nonce(self):
        res = requests.get(f"{self.node_url}/nonce")
        logging.debug(res)
        return res.json()

    def get_latest_block(self):
        res = requests.get(f"{self.node_url}/latest_block")
        logging.debug(res)
        return res.json()

    def get_latest_block_number(self):
        res = requests.get(f"{self.node_url}/latest_block_num")
        logging.debug(res)
        return res.json()["latest_block_number"]

    def get_balance(self, address):
        contract = self.client.get_contract("currency")
        res = contract.quick_read('balance_of', address)
        logging.debug(res)
        return res
