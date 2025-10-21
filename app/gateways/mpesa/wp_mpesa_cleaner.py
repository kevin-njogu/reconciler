from app.gateways.workpay_cleaner import WorkpayCleaner

class WorkpayMpesaCleaner(WorkpayCleaner):
    def __init__(self, configs, columns, name):
        super().__init__(configs, columns, name)


