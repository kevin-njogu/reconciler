from typing import Optional, Callable, Tuple

import pandas as pd
import numpy as np
from sqlalchemy.exc import IntegrityError

from app.database.mysql_configs import get_database
from app.exceptions.exceptions import ReconciliationException, DbOperationException
from sqlalchemy.orm import Session

from app.gateways.equity.entities import EquityDebit, EquityCredit, EquityCharge, WorkpayEquityPayout, \
    WorkpayEquityRefund, WorkpayTopUp
from app.gateways.equity.models import EquityTransactionBase, WorkpayEquityTransactionBase
from app.gateways.kcb.entities import KcbDebit, KcbCredit, KcbCharge, WorkpayKcbPayout, WorkpayKcbRefund
from app.gateways.kcb.models import KcbTransactionBase, WorkpayKcbTransactionBase
from app.gateways.mpesa.entities import WorkpayMpesaPayout, WorkpayMpesaRefund, MpesaDebit, MpesaCredit, MpesaCharge
from app.gateways.mpesa.models import MpesaTransactionBase, WorkpayMpesaTransactionBase


class EquityGatewayReconciler:

    def __init__(self, session_id: str, gateway_configs, workpay_configs, gateway_name: str, db_session:Session,
                 gateway_file_factory: Optional[Callable[[str], object]] = None,
                 workpay_file_factory: Optional[Callable[[str], object]] = None):
        self.session_id = session_id
        self.db_session = db_session
        self.gateway_name = gateway_name
        self.gateway_configs = gateway_configs
        self.workpay_configs = workpay_configs
        self.gateway_file_factory = gateway_file_factory
        self.workpay_file_factory = workpay_file_factory
        self.gateway_debits: Optional[pd.DataFrame] = None
        self.gateway_credits: Optional[pd.DataFrame] = None
        self.gateway_charges: Optional[pd.DataFrame] = None
        self.workpay_payouts_data: Optional[pd.DataFrame] = None
        self.workpay_refunds: Optional[pd.DataFrame] = None
        self.workpay_top_ups: Optional[pd.DataFrame] = None
        self.gateway_matching_column = gateway_configs.MATCHING_COLUMN
        self.workpay_matching_column = workpay_configs.MATCHING_COLUMN
        self.gateway_slice_columns = gateway_configs.GATEWAY_SLICE_COLUMNS
        self.workpay_slice_columns = workpay_configs.WORKPAY_SLICE_COLUMNS


    def _create_gateway_file_class(self):
        if self.gateway_file_factory:
            return self.gateway_file_factory(self.session_id)
        from app.gateways.equity.GatewayFileClass import GatewayFile
        return GatewayFile(self.session_id, self.gateway_configs)


    def _create_workpay_file_class(self):
        if self.workpay_file_factory:
            return self.workpay_file_factory(self.session_id)
        from app.gateways.equity.WorkpayFIleClass import WorkpayFIle
        return WorkpayFIle(self.session_id, self.workpay_configs)


    def load_dataframes(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        workpay_top_ups = pd.DataFrame()
        try:
            gateway_processor = self._create_gateway_file_class()
            workpay_processor = self._create_workpay_file_class()
        except Exception as e:
            raise ReconciliationException("Failed to initialize file processors") from e

        #Load equity credits
        try:
            gateway_credits = gateway_processor.get_equity_credits()
            gateway_credits["Reconciliation Status"] = "Reconciled"
            gateway_credits["Reconciliation Session"] = self.session_id
        except Exception as e:
            raise ReconciliationException("Failed to load gateway credits") from e

        #Load equity charges
        try:
            gateway_charges = gateway_processor.get_equity_charges()
            gateway_charges["Reconciliation Status"] = "Reconciled"
            gateway_charges["Reconciliation Session"] = self.session_id
        except Exception as e:
            raise ReconciliationException("Failed to load gateway charges") from e

        # Load equity bank debits
        try:
            gateway_debits = gateway_processor.get_equity_debits()
            gateway_debits["Reconciliation Status"] = "Unreconciled"
            gateway_debits["Reconciliation Session"] = self.session_id
        except Exception as e:
            raise ReconciliationException("Failed to load gateway debits") from e

        # Load workpay refunds
        try:
            workpay_refunds = workpay_processor.get_workpay_equity_refunds()
            workpay_refunds["Reconciliation Status"] = "Reconciled"
            workpay_refunds["Reconciliation Session"] = self.session_id
        except Exception as e:
            raise ReconciliationException("Failed to load workpay refunds") from e

        # Load workpay top ups
        if self.gateway_name == "equity":
            try:
                workpay_top_ups = workpay_processor.get_workpay_equity_top_ups()
                workpay_top_ups["Reconciliation Status"] = "Reconciled"
                workpay_top_ups["Reconciliation Session"] = self.session_id
            except Exception as e:
                raise ReconciliationException("Failed to load workpay top ups") from e

        # Load workpay payouts
        try:
            workpay_payouts = workpay_processor.get_workpay_equity_payouts()
            workpay_payouts["Reconciliation Status"] = "Unreconciled"
            workpay_payouts["Reconciliation Session"] = self.session_id
        except Exception as e:
            raise ReconciliationException("Failed to load workpay payouts") from e

        # Validate results
        if gateway_debits is None or workpay_payouts is None:
            raise ReconciliationException("One of the dataframes returned None")

        if not isinstance(gateway_debits, pd.DataFrame) or not isinstance(workpay_payouts, pd.DataFrame):
            raise ReconciliationException("Loaded objects are not pandas DataFrames")

        # Check emptiness
        if gateway_debits.empty or workpay_payouts.empty:
            raise ReconciliationException("Could not load equity bank debits or workpay equity payouts (empty)")

        self.gateway_debits = gateway_debits.copy()
        self.workpay_payouts_data = workpay_payouts.copy()
        self.gateway_credits = gateway_credits.copy()
        self.gateway_charges = gateway_charges.copy()
        self.workpay_refunds = workpay_refunds.copy()
        if self.gateway_name == "equity":
            self.workpay_top_ups = workpay_top_ups.copy()

        return self.gateway_debits, self.workpay_payouts_data


    def reconcile_equity(self):
        if self.gateway_debits is None or self.workpay_payouts_data is None:
            self.load_dataframes()

        gateway_df = self.gateway_debits
        workpay_df = self.workpay_payouts_data

        #Validate matching column exists in WorkPay ---
        wp_col = self.workpay_matching_column
        if wp_col not in workpay_df.columns:
            raise ReconciliationException(
                f"Missing required column '{wp_col}' in WorkPay equity payouts dataframe."
            )
        workpay_df[wp_col] = workpay_df[wp_col].fillna("").astype(str).str.strip()

        equity_match_col = self.gateway_matching_column
        if equity_match_col not in gateway_df.columns:
            raise ReconciliationException(
                f"Missing required column '{equity_match_col}' in Equity bank dataframe."
            )
        gateway_df[equity_match_col] = gateway_df[equity_match_col].fillna("").astype(str)

        equity_refs = set(gateway_df[equity_match_col])
        workpay_df["Reconciliation Status"] = np.where(
            workpay_df[wp_col].isin(equity_refs),
            "Reconciled",
            "Unreconciled"
        )

        wp_refs = set(workpay_df[wp_col])
        gateway_df["Reconciliation Status"] = np.where(
            gateway_df[equity_match_col].isin(wp_refs),
            "Reconciled",
            "Unreconciled"
        )

        if gateway_df.empty or workpay_df.empty:
            raise ReconciliationException("Equity debits or workpay payouts is empty")

        self.gateway_debits = gateway_df
        self.workpay_payouts_data = workpay_df

        return gateway_df, workpay_df


    def save_reconciled(self):
        self.load_dataframes()
        self.reconcile_equity()

        mappings = {}

        gateway_debits = self.gateway_debits[self.gateway_slice_columns]
        gateway_credits = self.gateway_credits[self.gateway_slice_columns]
        gateway_charges = self.gateway_charges[self.gateway_slice_columns]
        workpay_payouts = self.workpay_payouts_data[self.workpay_slice_columns]
        workpay_refunds = self.workpay_refunds[self.workpay_slice_columns]
        if self.gateway_name.lower() == "equity":
            workpay_top_ups = self.workpay_top_ups[self.workpay_slice_columns]

        if self.gateway_name.lower() == "equity":
            mappings = self.generate_equity_mappings(gateway_debits, gateway_credits, gateway_charges,
                                                     workpay_payouts, workpay_refunds, workpay_top_ups)
        elif self.gateway_name.lower() == "kcb":
            mappings = self.generate_kcb_mappings(gateway_debits, gateway_credits, gateway_charges,
                                                     workpay_payouts, workpay_refunds)
        elif self.gateway_name.lower() == "mpesa":
            mappings = self.generate_mpesa_mappings(gateway_debits, gateway_credits, gateway_charges,
                                                  workpay_payouts, workpay_refunds)
        try:
            with self.db_session.begin():
                for key, (df, pydantic_model, entity) in mappings.items():
                    if df is None or df.empty:
                        continue

                    records = df.to_dict("records")
                    validated = [pydantic_model(**rec) for rec in records]
                    payload = [v.model_dump() for v in validated]

                    self.db_session.bulk_insert_mappings(entity, payload)
            return "Reconciliation process completed"

        except IntegrityError as e:
            self.db_session.rollback()
            raise DbOperationException(f"Duplicate entry detected {e}")
        except Exception:
            self.db_session.rollback()
            raise


    def generate_equity_mappings(self,
                                 bank_debits: pd.DataFrame,
                                 bank_credits: pd.DataFrame,
                                 bank_charges: pd.DataFrame,
                                 workpay_payouts: pd.DataFrame,
                                 workpay_refunds: pd.DataFrame,
                                 workpay_top_ups: pd.DataFrame
                                 ):
        mappings = {
            "bank_debits": [bank_debits, EquityTransactionBase, EquityDebit],
            "bank_credits": [bank_credits, EquityTransactionBase, EquityCredit],
            "bank_charges": [bank_charges, EquityTransactionBase, EquityCharge],
            "workpay_payout": [workpay_payouts, WorkpayEquityTransactionBase, WorkpayEquityPayout],
            "workpay_refunds": [workpay_refunds, WorkpayEquityTransactionBase, WorkpayEquityRefund],
            "workpay_top_ups": [workpay_top_ups, WorkpayEquityTransactionBase, WorkpayTopUp],
        }
        return mappings


    def generate_kcb_mappings(self,
                                 bank_debits: pd.DataFrame,
                                 bank_credits: pd.DataFrame,
                                 bank_charges: pd.DataFrame,
                                 workpay_payouts: pd.DataFrame,
                                 workpay_refunds: pd.DataFrame,
                                 ):
        mappings = {
            "bank_debits": [bank_debits, KcbTransactionBase, KcbDebit],
            "bank_credits": [bank_credits, KcbTransactionBase, KcbCredit],
            "bank_charges": [bank_charges, KcbTransactionBase, KcbCharge],
            "workpay_payout": [workpay_payouts, WorkpayKcbTransactionBase, WorkpayKcbPayout],
            "workpay_refunds": [workpay_refunds, WorkpayKcbTransactionBase, WorkpayKcbRefund],
        }
        return mappings


    def generate_mpesa_mappings(self,
                                 bank_debits: pd.DataFrame,
                                 bank_credits: pd.DataFrame,
                                 bank_charges: pd.DataFrame,
                                 workpay_payouts: pd.DataFrame,
                                 workpay_refunds: pd.DataFrame,
                                 ):
        mappings = {
            "bank_debits": [bank_debits, MpesaTransactionBase, MpesaDebit],
            "bank_credits": [bank_credits, MpesaTransactionBase, MpesaCredit],
            "bank_charges": [bank_charges, MpesaTransactionBase, MpesaCharge],
            "workpay_payout": [workpay_payouts, WorkpayMpesaTransactionBase, WorkpayMpesaPayout],
            "workpay_refunds": [workpay_refunds, WorkpayMpesaTransactionBase, WorkpayMpesaRefund],
        }
        return mappings


# reconciler = EquityGatewayReconciler("sess:2025-11-21_06:29:47")
# bank, internal = reconciler.load_dataframes()
# bank, internal = reconciler.reconcile_equity()
# print(internal["API Reference"])
# reconciler.save_reconciled()
