from fastapi import HTTPException
from rapidfuzz import fuzz, process
import pandas as pd
import numpy as np
from app.gateways.equity.equity import Equity
from app.gateways.kcb.kcb import KCB
from app.gateways.mpesa.mpesa_mmf import MpesaMmf
from app.gateways.mpesa.mpesa_utility import MpesaUtility
from app.gateways.workpay_equity.equity_workpay import EquityWorkpay
from app.gateways.workpay_kcb.kcb_workpay import KCBWorkpay
from app.gateways.workpay_mpesa.mpesa_workpay import MpesaWorkpay
from app.utils.get_current_session import get_current_session
from app.utils.get_uploads_dir import get_uploads_dir

# sess = get_current_session()
# dir_uploads = get_uploads_dir(sess)

class Reconcile:

    def __init__(self, session, uploads_dir):
        self.session = session
        self.uploads_dir = uploads_dir
        self.threshold = 90


    def reconcile_mpesa(self):
        try:
            wp_mpesa = MpesaWorkpay(self.session, self.uploads_dir)
            workpay_mp = wp_mpesa.clean_data()
            mmf = MpesaMmf(self.session, self.uploads_dir)
            _, _, mmf_debits = mmf.filter_data()
            utility = MpesaUtility(self.session, self.uploads_dir)
            _, _, utility_debits = utility.filter_data()

            mmf_data =mmf_debits.copy()
            utility_data = utility_debits.copy()
            backend_data = workpay_mp.copy()
            backend_refs = backend_data['reference'].astype(str).tolist()

            mmf_matches = []
            for text in mmf_data['narrative'].astype(str):
                match, score, _ = process.extractOne(text, backend_refs, scorer=fuzz.token_sort_ratio) or (None, 0, None)
                mmf_matches.append(score >= self.threshold)
            mmf_data['status'] = ['Reconciled' if x else 'Unreconciled' for x in mmf_matches]

            # --- Utility vs Backend ---
            utility_matches = []
            for text in utility_data['narrative'].astype(str):
                match, score, _ = process.extractOne(text, backend_refs, scorer=fuzz.token_sort_ratio) or (None, 0, None)
                utility_matches.append(score >= self.threshold)
            utility_data['status'] = ['Reconciled' if x else 'Unreconciled' for x in utility_matches]

            # --- Backend vs MMF + Utility ---
            mmf_refs = mmf_data['narrative'].astype(str).tolist()
            utility_refs = utility_data['narrative'].astype(str).tolist()

            backend_matches = []
            for ref in backend_data['reference'].astype(str):
                # Try matching against both lists
                mmf_match, mmf_score, _ = process.extractOne(ref, mmf_refs, scorer=fuzz.token_sort_ratio) or (None, 0, None)
                util_match, util_score, _ = process.extractOne(ref, utility_refs, scorer=fuzz.token_sort_ratio) or (None, 0, None)

                # Take best of the two
                best_score = max(mmf_score, util_score)
                backend_matches.append(best_score >= self.threshold)
            backend_data['status'] = ['Reconciled' if x else 'Unreconciled' for x in backend_matches]

            # print(utility_data)
            return mmf_data, utility_data, backend_data
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def reconcile_equity(self):
        try:
            wp_equity = EquityWorkpay(self.session, self.uploads_dir)
            workpay_eq = wp_equity.clean_data()
            equity = Equity(self.session, self.uploads_dir)
            _, _, eq_debits = equity.filter_data()

            equity_data = eq_debits.copy().reset_index(drop=True)
            backend_data = workpay_eq.copy().reset_index(drop=True)

            equity_refs = equity_data['narrative'].astype(str).tolist()
            backend_refs = backend_data['reference'].astype(str).tolist()

            equity_data['matched_reference'] = None

            for i, eq_ref in enumerate(equity_refs):
                match, score, _ = process.extractOne(eq_ref, backend_refs, scorer=fuzz.partial_ratio) or (None, 0, None)

                equity_data.loc[i, 'matched_reference'] = match
                equity_data.loc[i, 'status'] = 'Reconciled' if score >= self.threshold else 'Unreconciled'

            # Optional: also mark backend refs as matched if they appear in any reconciled row
            matched_refs = equity_data.loc[equity_data['status'] == 'Reconciled', 'matched_reference']
            backend_data['status'] = backend_data['reference'].isin(matched_refs)
            backend_data['status'] = backend_data['status'].map({True: 'Reconciled', False: 'Unreconciled'})

            equity_data = equity_data.drop(columns=['matched_reference'])

            # print(equity_data)
            return equity_data, backend_data
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    def reconcile_kcb(self):
        try:
            wp_kcb = KCBWorkpay(self.session, self.uploads_dir)
            workpay_kcb = wp_kcb.clean_data()
            kcb = KCB(self.session, self.uploads_dir)
            _, _, kcb_debits = kcb.filter_data()

            kcb_data = kcb_debits.copy()
            backend_data = workpay_kcb.copy()

            kcb_narratives = kcb_data['narrative'].astype(str).tolist()
            backend_refs = backend_data['reference'].astype(str).tolist()

            # Vectorized similarity computation
            scores = process.cdist(kcb_narratives, backend_refs, scorer=fuzz.partial_ratio)
            max_scores = np.max(scores, axis=1)
            best_matches = [backend_refs[i] for i in np.argmax(scores, axis=1)]

            kcb_data['match_score'] = max_scores
            kcb_data['matched_reference'] = best_matches
            kcb_data['status'] = np.where(max_scores >= self.threshold, 'Reconciled', 'Unreconciled')

            # Mark backend matches
            reconciled_refs = set(kcb_data.loc[kcb_data['status'] == 'Reconciled', 'matched_reference'])
            backend_data['status'] = backend_data['reference'].isin(reconciled_refs)
            backend_data['status'] = backend_data['status'].map({True: 'Reconciled', False: 'Unreconciled'})

            kcb_data = kcb_data.drop(columns=['match_score', 'matched_reference'])

            # print(backend_data)
            return kcb_data, backend_data
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))



# wp_equity = EquityWorkpay(sess, dir_uploads)
# workpay_eq = wp_equity.clean_data()
#
# equity = Equity(sess, dir_uploads)
# _, _, eq_debits = equity.filter_data()
#
# wp_mpesa = MpesaWorkpay(sess, dir_uploads)
# workpay_mp = wp_mpesa.clean_data()
#
# mmf = MpesaMmf(sess, dir_uploads)
# _, _, mmf_debits = mmf.filter_data()
#
# utility = MpesaUtility(sess, dir_uploads)
# _, _, utility_debits = utility.filter_data()
#
# wp_kcb = KCBWorkpay(sess, dir_uploads)
# workpay_kcb = wp_kcb.clean_data()
#
# kcb = KCB(sess, dir_uploads)
# _, _, kcb_debits = kcb.filter_data()


#recon = Reconcile(workpay_eq, eq_debits, workpay_mp, mmf_debits, utility_debits, workpay_kcb, kcb_debits)
# recon.reconcile_mpesa()
# recon.reconcile_equity()
# recon.reconcile_kcb()