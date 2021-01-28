import os
import logging
import requests
import tgbf.constants as c

from enum import Enum
from tgbf.config import ConfigManager as Cfg
from tgbf.lamden.wallet import LamdenWallet
from tgbf.lamden.lamden import Lamden


class Chain(Enum):
    MAIN = 1
    TEST = 2


class LamdenConnect(Lamden):

    def __init__(self, chain: Chain = Chain.MAIN, wallet: LamdenWallet = None):
        self.cfg = Cfg(os.path.join(c.DIR_CFG, "lamden.json"))
        self.chain = chain

        host, port = self.connect()

        super().__init__(host=host, port=port, wallet=wallet)

    def connect(self):
        for chain, node_list in self.cfg.get("masternodes").items():
            if chain == self.chain.name:
                for node in node_list:
                    for host, port in node.items():
                        try:
                            self.ping(host, port)
                            return host, port
                        except:
                            msg = f"Can not connect to host '{host}' and port '{port}'"
                            logging.info(msg)

        raise ConnectionError("Can not connect to network")

    @staticmethod
    def ping(host: str, port: int):
        node = host if port is None else f"{host}:{port}"
        res = requests.get(f"{node}/ping").json()

        if "status" not in res or res["status"] != "online":
            raise ConnectionError(f"Unexpected result: {res}")

        return res
