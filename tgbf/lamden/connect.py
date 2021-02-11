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

        host, port = self.connect()
        super().__init__(host=host, port=port, wallet=wallet)

    def connect(self):
        for chain, node_list in self.cfg.get("masternodes").items():
            if chain.lower() == self.chain.lower():
                for node in node_list:
                    for host, port in node.items():
                        try:
                            self.ping(host, port)
                            return host, port
                        except:
                            msg = f"Can not connect to host '{host}' and port '{port}'"
                            logging.warning(msg)

        raise ConnectionError("Can not connect to network")

    @staticmethod
    def ping(host: str, port: int):
        node = host if port is None else f"{host}:{port}"
        res = requests.get(f"{node}/ping").json()

        if "status" not in res or res["status"] != "online":
            raise ConnectionError(f"Unexpected result: {res}")

        return res
