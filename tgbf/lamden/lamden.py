import requests

from tgbf.lamden.wallet import LamdenWallet
#from contracting.client import ContractingClient


class Lamden:

    def __init__(self, host: str = None, port: int = None, wallet: LamdenWallet = None):
        self.host = host
        self.port = port
        self.wallet = wallet
        self._node_url = None

        # Make sure mongodb instance is running or otherwise you get this error:
        # "Process finished with exit code 139 (interrupted by signal 11: SIGSEGV)"
        # https://blog.lamden.io/smart-contracting-with-python-2af233620dca
        #self.client = ContractingClient()

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
        else:
            balance = res.json()["value"]
            return "0" if balance is None else balance["__fixed__"]  # FIXME: No '__fixed__' if on testnet

    def get_contracts(self):
        res = requests.get(f"{self.node_url}/contracts")
        return res.json()

    def get_transaction_details(self, tx_hash):
        res = requests.get(f"{self.node_url}/tx?hash={tx_hash}")
        return res.json()

    def post_transaction(self):
        res = requests.post(f"{self.node_url}/")
        # TODO

    def get_network_constitution(self):
        res = requests.get(f"{self.node_url}/constitution")
        return res.json()

    def get_contract_methods(self):
        res = requests.get(f"{self.node_url}/contracts/currency/methods")
        return res.json()

    def get_contract_variables(self):
        res = requests.get(f"{self.node_url}/contracts/currency/variables")
        return res.json()
