import os
import logging
import requests
import tgbf.constants as c

from tgbf.config import ConfigManager as Cfg
from lamden.crypto.wallet import Wallet
from tgbf.lamden.api import API


class Connect(API):

    def __init__(self, wallet: Wallet = None):
        self.cfg = Cfg(os.path.join(c.DIR_CFG, "lamden.json"))
        self.chain = self.cfg.get("chain")

        node_host, node_port, explorer_host, explorer_port = self.connect()
        wallet = wallet if wallet else Wallet()

        super().__init__(
            node_host=node_host,
            node_port=node_port,
            wallet=wallet,
            explorer_host=explorer_host,
            explorer_port=explorer_port)

    def connect(self):
        explorer_dict = self.cfg.get(self.chain)["explorer"]
        explorer_host = next(iter(explorer_dict))
        explorer_port = explorer_dict[explorer_host]

        node_list = self.cfg.get(self.chain)["masternodes"]
        for node in node_list:
            for node_host, node_port in node.items():
                try:
                    self.ping(node_host, node_port)
                    return node_host, node_port, explorer_host, explorer_port
                except:
                    msg = f"Can not connect to host '{node_host}' and port '{node_port}'"
                    logging.warning(msg)

        raise ConnectionError("Can not connect to network")

    @staticmethod
    def ping(host: str, port: int):
        node = host if port is None else f"{host}:{port}"
        res = requests.get(f"{node}/ping").json()

        if "status" not in res or res["status"] != "online":
            raise ConnectionError(f"Unexpected result: {res}")

        return res
