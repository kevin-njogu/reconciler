from typing import List

import pandas as pd
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.database.database_connection import get_db_session
from app.models.all_models import *
from app.models.base_models import *
from app.reconciliation.reconciliation import Reconcile
from app.utils.get_current_session import get_current_session
from app.utils.get_uploads_dir import get_uploads_dir


class UploadService:

    def db_upload(self, records):
        with get_db_session() as db:
            try:
                for item in records:
                    for record in item:
                        db.add(record)
                db.commit()
            except IntegrityError:
                db.rollback()
                raise HTTPException(status_code=400, detail="Integrity error — nothing saved")
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=400, detail=str(e))


    def upload_func(self, gateway: str):
        try:
            session_id = get_current_session()
            dir_uploads = get_uploads_dir(session_id)

            recon = Reconcile(session_id, dir_uploads)

            if gateway.lower() == "equity":
                equity_data, backend_data = recon.reconcile_equity()

                equity_data['session_id'] = session_id
                backend_data['session_id'] = session_id

                equity_df = equity_data.to_dict('records')
                backend_df = backend_data.to_dict('records')

                equity_validated_records = [EquityDebitBase(**record) for record in equity_df]
                backend_validated_records = [EquityWorkpayBase(**record) for record in backend_df]

                equity_db_records = [EquityDebits(**record.model_dump()) for record in equity_validated_records]
                backend_db_records = [EquityWorkpay(**record.model_dump()) for record in backend_validated_records]

                self.db_upload([equity_db_records, backend_db_records])
            elif gateway.lower() == "mpesa":
                mmf_data, utility_data, backend_data = recon.reconcile_mpesa()

                mmf_data['session_id'] = session_id
                utility_data['session_id'] = session_id
                backend_data['session_id'] = session_id

                #print(mmf_data)

                mmf_df = mmf_data.to_dict('records')
                utility_df = utility_data.to_dict('records')
                backend_df = backend_data.to_dict('records')

                mmf_validated_records = [MMFDebitBase(**record) for record in mmf_df]
                utility_validated_records = [UtilityDebitBase(**record) for record in utility_df]
                backend_validated_records = [MpesaWorkpayBase(**record) for record in backend_df]

                mmf_db_records = [MMFDebit(**record.model_dump()) for record in mmf_validated_records]
                utility_db_records = [UtilityDebit(**record.model_dump()) for record in utility_validated_records]
                backend_db_records = [WorkpayMpesaTransaction(**record.model_dump()) for record in backend_validated_records]

                self.db_upload([mmf_db_records, utility_db_records, backend_db_records])
            elif gateway.lower() == "kcb":
                kcb_data, backend_data = recon.reconcile_kcb()

                kcb_data['session_id'] = session_id
                backend_data['session_id'] = session_id

                kcb_df = kcb_data.to_dict('records')
                backend_df = backend_data.to_dict('records')

                kcb_validated_records = [KcbDebitBase(**record) for record in kcb_df]
                backend_validated_records = [KcbWorkpayBase(**record) for record in backend_df]

                kcb_db_records = [KCBDebits(**record.model_dump()) for record in kcb_validated_records]
                backend_db_records = [KCBWorkpay(**record.model_dump()) for record in backend_validated_records]

                self.db_upload([kcb_db_records, backend_db_records])

        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

# upload = UploadService()
# upload.upload_func("kcb")