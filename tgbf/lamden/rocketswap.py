import requests


class Rocketswap:

    base_url = "https://rocketswap.exchange:2053/api/"

    def __init__(self, base_url=None):
        self.base_url = base_url if base_url else self.base_url

    def balances(self, address):
        with requests.get(self.base_url + "balances/" + address) as res:
            return res.json()

    def token_list(self):
        with requests.get(self.base_url + "token_list") as res:
            return res.json()

    def token(self, contract):
        with requests.get(self.base_url + "token/" + contract) as res:
            return res.json()

    def trade_history(self, take, skip):
        params = {"take": take, "skip": skip}
        with requests.get(self.base_url + "get_trade_history/", params=params) as res:
            return res.json()

    def get_market_summaries_w_token(self):
        with requests.get(self.base_url + "get_market_summaries_w_token") as res:
            return res.json()

    def user_lp_balance(self, address):
        with requests.get(self.base_url + "user_lp_balance/" + address) as res:
            return res.json()

    def get_pairs(self, contract):
        with requests.get(self.base_url + "get_pairs/" + contract) as res:
            return res.json()

    def user_staking_info(self, address):
        with requests.get(self.base_url + "user_staking_info/" + address) as res:
            return res.json()

    def staking_meta(self):
        with requests.get(self.base_url + "staking_meta") as res:
            return res.json()
