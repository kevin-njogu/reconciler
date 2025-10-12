from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO
import pandas as pd
from app.database.database_connection import get_db_session
from app.models.all_models import *
from app.utils.get_current_session import get_current_session

session_id = get_current_session()

class Reports:

    def download_report(self, session_id: str, gateway: str):
        with get_db_session() as db:
            try:
                gateway_dict = {
                    "equity":EquityDebits,
                    "wpequity": EquityWorkpay,
                    "mmf": MMFDebit,
                    "utility": UtilityDebit,
                    "wpmpesa": WorkpayMpesaTransaction,
                    "kcb": KCBDebits,
                    "wp-kcb": KCBWorkpay
                }
                selected_gateway = gateway_dict.get(gateway.lower())

                if not selected_gateway:
                    raise HTTPException(status_code=400, detail=f"Unknown gateway: {gateway}")

                records = db.query(selected_gateway).filter(selected_gateway.session_id == session_id).all()

                if not records:
                    raise HTTPException(status_code=404, detail="No records found for this session_id")

                df = pd.DataFrame([r.__dict__ for r in records])
                df = df.drop(columns=["_sa_instance_state"], errors="ignore")

                # df = df.drop(columns=["id", "session_id"])

                output = BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    df.to_excel(writer, index=False, sheet_name="Session_Report")

                output.seek(0)

                filename = f"{gateway}_{session_id}_report.xlsx"
                headers = {
                    "Content-Disposition": f"attachment; filename={filename}"
                }

                return StreamingResponse(
                    output,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers=headers
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

# report = Reports()
# report.download_report(session_id, 'wpmpesa')
