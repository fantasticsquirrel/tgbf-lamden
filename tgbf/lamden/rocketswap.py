import requests


class Rocketswap:

    base_url = "https://stats.rocketswap.exchange:2053/api/"

    def __init__(self, base_url=None):
        self.base_url = base_url if base_url else self.base_url

    def balances(self, address):
        return requests.get(self.base_url + "balances/" + address).json()

    def token_list(self):
        return requests.get(self.base_url + "token_list").json()

    def token(self, contract):
        return requests.get(self.base_url + "token/" + contract).json()

    def trade_history(self, take, skip):
        return requests.get(
            self.base_url + "get_trade_history/",
            params={"take": take, "skip": skip},
        ).json()

    def get_market_summaries_w_token(self):
        return requests.get(self.base_url + "get_market_summaries_w_token").json()
