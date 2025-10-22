from io import BytesIO

import pandas as pd
from fastapi import HTTPException
from rapidfuzz import fuzz, process
from sqlalchemy import select
from starlette.responses import StreamingResponse

from app.exceptions.exceptions import ServiceExecutionException
from app.gateways.equity.equity_bank_cleaner import EquityCleaner
from app.gateways.equity.entities import EquityDebit, EquityCharge, EquityCredit, WpEquityPayout, WpEquityRefund, TopUp
from app.gateways.equity.models import EquityTransactionBase, WorkpayEquityTransactionBase
from app.gateways.equity.wp_equity_cleaner import WorkpayEquityCleaner
from app.gateways.gateway_cleaner import GatewayCleaner
from app.gateways.kcb.entities import WpKcbRefund, WpKcbPayout, KcbDebit, KcbCredit, KcbCharge
from app.gateways.kcb.kcb_bank_cleaner import KcbCleaner
from app.gateways.kcb.models import WorkpayKcbTransactionBase, KcbTransactionBase
from app.gateways.kcb.wp_kcb_cleaner import WorkpayKcbCleaner
from app.gateways.mpesa.entities import MpesaWithdrawn, MpesaCharge, MpesaPaidIn, WpMpesaPayout, WpMpesaRefund
from app.gateways.mpesa.models import MpesaTransactionBase, WorkpayMpesaTransactionBase
from app.gateways.mpesa.mpesa_cleaner import MpesaMmfCleaner, MpesaUtilityCleaner
from app.gateways.mpesa.wp_mpesa_cleaner import WorkpayMpesaCleaner
from app.utils.constants import *
from app.utils.output_writer import write_to_excel


class CommonServices:

    def __init__(self, gateway, db_session, session_id):
        self.threshold = 85
        self.mmf = None
        self.utility = None
        self.wp_mpesa = None
        self.equity = None
        self.wp_equity = None
        self.kcb = None
        self.wp_kcb = None
        self.gateway = gateway
        self.db_session = db_session
        self.recon_session = session_id


    def reconcile(self, base_df: pd.DataFrame, *target_dfs: pd.DataFrame):
        try:
            internal_df = base_df.copy()
            internal_df['status'] = internal_df.get('status', pd.Series('Unreconciled', index=internal_df.index))
            reconciled_targets = []

            def reconcile_match(internal_ref, target_df, target_col, internal_col):
                match = process.extractOne(internal_ref, target_df[target_col], scorer=fuzz.partial_ratio)
                if match and match[1] >= self.threshold:
                    target_df.loc[target_df[target_col] == match[0], 'status'] = 'Reconciled'
                    internal_df.loc[internal_df[internal_col] == internal_ref, 'status'] = 'Reconciled'

            for target_df in target_dfs:
                target_df = target_df.copy()
                target_df['status'] = target_df.get('status', pd.Series('Unreconciled', index=target_df.index))
                # Define matching rules dynamically based on available columns
                if 'details' in target_df.columns and 'api_reference' in internal_df.columns:
                    for internal_ref in internal_df['api_reference']:
                        reconcile_match(internal_ref, target_df, 'details', 'api_reference')
                if 'reference' in target_df.columns and 'transaction_id' in internal_df.columns:
                    for internal_ref in internal_df['transaction_id']:
                        reconcile_match(internal_ref, target_df, 'reference', 'transaction_id')
                reconciled_targets.append(target_df)
            gateway_df = pd.concat(reconciled_targets, ignore_index=True)
            return gateway_df, internal_df
        except Exception as e:
            raise ServiceExecutionException(message=f"Failed to reconcile transactions {e}")


    def create_db_records(self, df: pd.DataFrame, pydantic_model, db_model, session_id:str):
        try:
            records = df.to_dict('records')
            print(records)
            validated_records = [pydantic_model(**record) for record in records]
            db_records = [db_model(**record.model_dump(), session_id=session_id) for record in validated_records]
            return db_records
        except Exception as e:
            raise ServiceExecutionException(message=f"Failed to create db records {e}")


    def instantiate_objects(self):
        gateway = self.gateway
        try:
            if gateway.lower() == "mpesa":
                self.mmf = MpesaMmfCleaner(FILE_CONFIGS_MMF, MPESA_COLUMNS)
                self.utility = MpesaUtilityCleaner(FILE_CONFIGS_UTILITY, MPESA_COLUMNS)
                self.wp_mpesa = WorkpayMpesaCleaner(FILE_CONFIGS_WORKPAY_MPESA, WP_COLS, gateway)
            elif gateway.lower() == "equity":
                self.equity = EquityCleaner(FILE_CONFIGS_EQUITY, EQUITY_COLUMNS)
                self.wp_equity = WorkpayEquityCleaner(FILE_CONFIGS_WORKPAY_EQUITY, WP_COLS, gateway)
            elif gateway.lower() == "kcb":
                self.kcb = KcbCleaner(FILE_CONFIGS_KCB, KCB_COLUMNS)
                self.wp_kcb = WorkpayKcbCleaner(FILE_CONFIGS_WORKPAY_KCB, WP_COLS, gateway)
        except Exception as e:
            raise ServiceExecutionException(message=f"Failed to instantiate objects {e}")


    def generate_dataframes(self):
        try:
            gateway = self.gateway
            if gateway.lower() == "mpesa":
                if not all ([self.wp_mpesa, self.utility, self.mmf]):
                    self.instantiate_objects()
                gateway_payouts, wp_payouts = self.reconcile(self.wp_mpesa.get_payouts(),
                                                             self.utility.get_debits(), self.mmf.get_debits())
                utility_charges, utility_deposits = self.utility.get_charges(), self.utility.get_credits()
                mmf_charges, mmf_deposits = self.mmf.get_charges(), self.mmf.get_credits()
                wp_refunds = self.wp_mpesa.get_refunds()
                return gateway_payouts, wp_payouts, utility_charges, utility_deposits, mmf_charges, mmf_deposits, wp_refunds
            elif gateway.lower() == "equity":
                if not all ([self.wp_equity, self.equity]):
                    self.instantiate_objects()
                gateway_payouts, wp_payouts = self.reconcile(self.wp_equity.get_payouts(),self.equity.get_debits())
                equity_charges, equity_deposits = self.equity.get_charges(), self.equity.get_credits()
                wp_refunds = self.wp_equity.get_refunds()
                top_ups = self.wp_equity.get_top_ups()
                return gateway_payouts, wp_payouts, equity_charges, equity_deposits, wp_refunds, top_ups
            elif gateway.lower() == "kcb":
                if not all ([self.wp_kcb, self.kcb]):
                    self.instantiate_objects()
                gateway_payouts, wp_payouts = self.reconcile(self.wp_kcb.get_payouts(), self.kcb.get_debits())
                kcb_charges, kcb_deposits = self.kcb.get_charges(), self.kcb.get_credits()
                wp_refunds = self.wp_kcb.get_refunds()
                return gateway_payouts, wp_payouts, kcb_charges, kcb_deposits, wp_refunds
        except Exception as e:
            raise ServiceExecutionException(message=f"Failed to instantiate object {e}")
        return None


    def generate_mpesa_mappings(self):
        try:
            gateway = self.gateway
            gateway_payouts, wp_payouts, utility_charges, utility_deposits, mmf_charges, mmf_deposits, wp_refunds = self.generate_dataframes()
            mpesa_charges = pd.concat([mmf_charges, utility_charges], ignore_index=True)
            mpesa_deposits = pd.concat([mmf_deposits, utility_deposits], ignore_index=True)
            mappings = {'mpesa_debits': [gateway_payouts, MpesaTransactionBase, MpesaWithdrawn],
                        'mpesa_deposits': [mpesa_deposits, MpesaTransactionBase, MpesaPaidIn],
                        'mpesa_charges': [mpesa_charges, MpesaTransactionBase, MpesaCharge],
                        'wp_payouts': [wp_payouts, WorkpayMpesaTransactionBase, WpMpesaPayout],
                        'wp_refunds': [wp_refunds, WorkpayMpesaTransactionBase, WpMpesaRefund]}
            return mappings
        except Exception as e:
            raise ServiceExecutionException(message=f"Failed to generate mpesa mappings {e}")

    def generate_equity_mappings(self):
        try:
            gateway_payouts, wp_payouts, equity_charges, equity_deposits, wp_refunds, top_ups = self.generate_dataframes()
            mappings = {'eq_debits': [gateway_payouts, EquityTransactionBase, EquityDebit],
                        'eq_credits': [equity_deposits, EquityTransactionBase, EquityCredit],
                        'eq_charges': [equity_charges, EquityTransactionBase, EquityCharge],
                        'wp_payouts': [wp_payouts, WorkpayEquityTransactionBase, WpEquityPayout],
                        'wp_refunds': [wp_refunds, WorkpayEquityTransactionBase, WpEquityRefund],
                        'top_ups': [top_ups, WorkpayEquityTransactionBase, TopUp]}
            return mappings
        except Exception as e:
            raise ServiceExecutionException(message=f"Failed to generate equity mappings {e}")

    def generate_kcb_mappings(self):
        try:
            gateway_payouts, wp_payouts, kcb_charges, kcb_deposits, wp_refunds = self.generate_dataframes()
            mappings = {'kcb_debits': [gateway_payouts, KcbTransactionBase, KcbDebit],
                        'kcb_credits': [kcb_deposits, KcbTransactionBase, KcbCredit],
                        'kcb_charges': [kcb_charges, KcbTransactionBase, KcbCharge],
                        'wp_payouts': [wp_payouts, WorkpayKcbTransactionBase, WpKcbPayout],
                        'wp_refunds': [wp_refunds, WorkpayKcbTransactionBase, WpKcbRefund]}
            return mappings
        except Exception as e:
            raise ServiceExecutionException(message=f"Failed to generate kcb mappings {e}")


    def save_reconciled(self):
        gateway = self.gateway
        session_id = self.recon_session
        db_session = self.db_session
        try:
            mappings = {}
            if gateway.lower() == "mpesa":
                mappings = self.generate_mpesa_mappings()
            elif gateway.lower() == "equity":
                mappings = self.generate_equity_mappings()
            elif gateway.lower() == "kcb":
                mappings = self.generate_kcb_mappings()

            for k, (df, schema, model) in mappings.items():
                db_record = self.create_db_records(df, schema, model, session_id)
                db_session.add_all(db_record)
                db_session.commit()
            return "Reconciliation process completed"
        except Exception as e:
            raise ServiceExecutionException(message=f"Failed to save reconciled items {e}")


    def map_to_schema(self, records, schema):
        return [schema.model_validate(record, from_attributes=True) for record in records]


    def schema_to_dataframe(self, schema_records):
        return pd.DataFrame([r.model_dump() for r in schema_records])


    def load_all(self, *models,):
        results = []
        for model in models:
            stmt = select(model).where(model.session_id == self.recon_session)
            records = self.db_session.execute(stmt).scalars().all()
            results.append(records)
        return results


    def map_mpesa(self):
        (mpesa_debits, mpesa_credits, mpesa_charges,
         wp_payouts, wp_refunds) = self.load_all(MpesaWithdrawn, MpesaPaidIn, MpesaCharge,
                                                 WpMpesaPayout, WpMpesaRefund)

        mpesa_debits_schema = self.map_to_schema(mpesa_debits, MpesaTransactionBase)
        mpesa_credits_schema = self.map_to_schema(mpesa_credits, MpesaTransactionBase)
        mpesa_charges_schema = self.map_to_schema(mpesa_charges, MpesaTransactionBase)
        wp_payouts_schema = self.map_to_schema(wp_payouts, WorkpayMpesaTransactionBase)
        wp_refunds_schema = self.map_to_schema(wp_refunds, WorkpayMpesaTransactionBase)
        schemas = {"mpesa_debits": mpesa_debits_schema, "mpesa_credits": mpesa_credits_schema,
                   "mpesa_charges": mpesa_charges_schema, "wp_payouts": wp_payouts_schema, "wp_refunds": wp_refunds_schema}
        return schemas


    def map_equity(self):
        (equity_debits, equity_credits, equity_charges,
         wp_payouts, wp_refunds, topups) = self.load_all(EquityDebit, EquityCredit, EquityCharge,
                                                 WpEquityPayout, WpEquityRefund,TopUp)

        equity_debits_schema = self.map_to_schema(equity_debits, EquityTransactionBase)
        equity_credits_schema = self.map_to_schema(equity_credits, EquityTransactionBase)
        equity_charges_schema = self.map_to_schema(equity_charges, EquityTransactionBase)
        wp_payouts_schema = self.map_to_schema(wp_payouts, WorkpayEquityTransactionBase)
        wp_refunds_schema = self.map_to_schema(wp_refunds, WorkpayEquityTransactionBase)
        topups_schema = self.map_to_schema(topups, WorkpayEquityTransactionBase)
        schemas = {"equity_debits": equity_debits_schema, "equity_credits": equity_credits_schema,
                   "equity_charges": equity_charges_schema, "wp_payouts": wp_payouts_schema, "wp_refunds": wp_refunds_schema,
                   "top_ups": topups_schema}
        return schemas

    def map_kcb(self):
        (kcb_debits, kcb_credits, kcb_charges,
         wp_payouts, wp_refunds) = self.load_all(KcbDebit, KcbCredit, KcbCharge,
                                                 WpEquityPayout, WpEquityRefund)

        kcb_debits_schema = self.map_to_schema(kcb_debits, KcbTransactionBase)
        kcb_credits_schema = self.map_to_schema(kcb_credits, KcbTransactionBase)
        kcb_charges_schema = self.map_to_schema(kcb_charges, KcbTransactionBase)
        wp_payouts_schema = self.map_to_schema(wp_payouts, WorkpayKcbTransactionBase)
        wp_refunds_schema = self.map_to_schema(wp_refunds, WorkpayKcbTransactionBase)
        schemas = {"kcb_debits": kcb_debits_schema, "kcb_credits": kcb_credits_schema,
                   "kcb_charges": kcb_charges_schema, "wp_payouts": wp_payouts_schema, "wp_refunds": wp_refunds_schema}
        return schemas



    def download_report(self):
        schemas = {}
        try:
            if self.gateway == "equity":
                schemas = self.map_equity()
            elif self.gateway == "mpesa":
                schemas = self.map_mpesa()
            elif self.gateway == "kcb":
                schemas = self.map_kcb()

            dataframes = {name: self.schema_to_dataframe(records) for name, records in schemas.items()}

            output = BytesIO()
            write_to_excel(output, dataframes)
            output.seek(0)

            filename = f"{self.gateway.capitalize()}_{self.recon_session}_report.xlsx"
            headers = {
                "Content-Disposition": f"attachment; filename={filename}"
            }
            return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                     headers=headers)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))



# from app.database.mysql_configs import Session, get_database
# from app.database.redis_configs import get_current_redis_session_id
# db = next(get_database())
# session = get_current_redis_session_id()
# service = CommonServices("mpesa", db, session)
# response = service.download_report()

# utility_reconciler = GatewayCleaner(FILE_CONFIGS_UTILITY, MPESA_COLUMNS)
# util_debits = utility_reconciler.get_debits()
# mmf_reconciler = GatewayCleaner(FILE_CONFIGS_MMF, MPESA_COLUMNS)
# mmf_debits = mmf_reconciler.get_debits()
# df_wp_mpesa = Workpay(FILE_CONFIGS_WORKPAY_MPESA, WP_COLS)
# wp_debits = df_wp_mpesa.get_payouts()
#
# eq_reconciler = EquityCleaner(FILE_CONFIGS_EQUITY, EQUITY_COLUMNS)
# eq_debits = eq_reconciler.get_debits()
# wp_equity = WorkpayReconciler(FILE_CONFIGS_WORKPAY_EQUITY, WP_COLS)
# wp_eq_debits = wp_equity.get_payouts()
#
# services = CommonServices("equity", db, session)
#
# gateway_df, internal_df = services.reconcile(wp_eq_debits, eq_debits)
# print(gateway_df)

