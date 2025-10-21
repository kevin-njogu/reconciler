from app.gateways.gateway_cleaner import GatewayCleaner


class MpesaMmfCleaner(GatewayCleaner):
    def __init__(self, configs, columns):
        super().__init__(configs, columns)


class MpesaUtilityCleaner(GatewayCleaner):
    def __init__(self, configs, columns):
        super().__init__(configs, columns)
