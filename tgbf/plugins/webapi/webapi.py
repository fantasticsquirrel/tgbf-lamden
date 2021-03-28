from tgbf.plugin import TGBFPlugin
from tgbf.web import EndpointAction


class Webapi(TGBFPlugin):

    def load(self):
        action = EndpointAction(self.addresses_callback, None)
        self.add_endpoint("addresses", action)

    def addresses_callback(self):
        sql = self.get_global_resource("select_addresses.sql")
        res = self.execute_global_sql(sql)

        if not res["data"]:
            return {"error": "No data"}

        return dict(res["data"])
