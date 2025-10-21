from app.gateways.gateway_cleaner import GatewayCleaner


class EquityCleaner(GatewayCleaner):
    def __init__(self, configs, columns):
        super().__init__(configs, columns)
