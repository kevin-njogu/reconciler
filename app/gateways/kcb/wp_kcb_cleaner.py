from app.gateways.workpay_cleaner import WorkpayCleaner


class WorkpayKcbCleaner(WorkpayCleaner):
    def __init__(self, configs, columns, name):
        super().__init__(configs, columns, name)
