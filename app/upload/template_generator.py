import logging
from datetime import date
from enum import Enum
from io import BytesIO

import pandas as pd

from app.exceptions.exceptions import FileUploadException

logger = logging.getLogger("app.template_generator")


class TemplateFormat(Enum):
    XLSX = "xlsx"
    CSV = "csv"


# Template column names
DATE_COLUMN = "Date"
REFERENCE_COLUMN = "Reference"
DETAILS_COLUMN = "Details"
DEBIT_COLUMN = "Debit"
CREDIT_COLUMN = "Credit"

# Backwards-compatible aliases for old column names
TRANSACTION_ID_COLUMN = REFERENCE_COLUMN
NARRATIVE_COLUMN = DETAILS_COLUMN

# Required columns for the unified template
DEFAULT_TEMPLATE_COLUMNS = [
    DATE_COLUMN,
    REFERENCE_COLUMN,
    DETAILS_COLUMN,
    DEBIT_COLUMN,
    CREDIT_COLUMN,
]

# Backwards compatibility alias
TEMPLATE_COLUMNS = DEFAULT_TEMPLATE_COLUMNS

# Date format for the template (YYYY-MM-DD)
TEMPLATE_DATE_FORMAT = "%Y-%m-%d"


class TemplateGenerator:
    """
    Generates upload template for file uploads.

    Template columns:
    - Date: YYYY-MM-DD format (mandatory)
    - Reference: Unique transaction identifier (mandatory)
    - Details: Transaction description/narration (mandatory)
    - Debit: Debit amount - numeric (optional, can be empty)
    - Credit: Credit amount - numeric (optional, can be empty)

    The same template is used for all gateways.
    Gateway distinction is made by the filename prefix during upload.
    """

    XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    CSV_CONTENT_TYPE = "text/csv"

    def _validate_date(self, template_date: date) -> str:
        """
        Validate and format the template date.

        Args:
            template_date: Date to format.

        Returns:
            Date string in YYYY-MM-DD format.

        Raises:
            FileUploadException: If date is not provided.
        """
        if not template_date:
            raise FileUploadException("Date is required")
        return template_date.strftime(TEMPLATE_DATE_FORMAT)

    def _write_to_xlsx(self, df: pd.DataFrame) -> bytes:
        """Write DataFrame to xlsx bytes."""
        buffer = BytesIO()
        df.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)
        return buffer.getvalue()

    def _write_to_csv(self, df: pd.DataFrame) -> bytes:
        """Write DataFrame to csv bytes."""
        buffer = BytesIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        return buffer.getvalue()

    def generate_template(
        self,
        template_date: date,
        format: TemplateFormat = TemplateFormat.XLSX
    ) -> bytes:
        """
        Generate upload template.

        The template has a single sample row with the current date in YYYY-MM-DD format
        to guide the user on the expected date format.

        Args:
            template_date: Date to fill in the Date column as guidance.
            format: Output format (XLSX or CSV).

        Returns:
            File content as bytes.
        """
        try:
            formatted_date = self._validate_date(template_date)
            logger.debug(f"Generating template with date: {formatted_date}, format: {format.value}")

            # Create template with sample row showing expected format
            data = {
                DATE_COLUMN: [formatted_date],
                REFERENCE_COLUMN: [""],
                DETAILS_COLUMN: [""],
                DEBIT_COLUMN: [""],
                CREDIT_COLUMN: [""],
            }

            df = pd.DataFrame(data)

            if format == TemplateFormat.CSV:
                content = self._write_to_csv(df)
            else:
                content = self._write_to_xlsx(df)

            logger.info(f"Template generated successfully: format={format.value}")
            return content

        except FileUploadException:
            raise
        except Exception as e:
            logger.error(f"Failed to generate template: {str(e)}", exc_info=True)
            raise FileUploadException(f"Failed to generate template: {str(e)}")

    def get_template_filename(self, format: TemplateFormat = TemplateFormat.XLSX) -> str:
        """Get filename for template."""
        ext = "csv" if format == TemplateFormat.CSV else "xlsx"
        return f"template.{ext}"

    def get_content_type(self, format: TemplateFormat = TemplateFormat.XLSX) -> str:
        """Get MIME content type."""
        if format == TemplateFormat.CSV:
            return self.CSV_CONTENT_TYPE
        return self.XLSX_CONTENT_TYPE

    @staticmethod
    def get_column_info() -> dict:
        """
        Get template column information for the download popup.

        Returns:
            Dictionary with column details including name, description,
            format, and whether the column is mandatory.
        """
        return {
            "columns": [
                {
                    "name": DATE_COLUMN,
                    "description": "Transaction date",
                    "format": "YYYY-MM-DD",
                    "mandatory": True,
                    "example": "2026-01-24",
                },
                {
                    "name": REFERENCE_COLUMN,
                    "description": "Unique transaction identifier (Transaction ID)",
                    "format": "Text/Number",
                    "mandatory": True,
                    "example": "TXN123456",
                },
                {
                    "name": DETAILS_COLUMN,
                    "description": "Transaction narration/description",
                    "format": "Text",
                    "mandatory": True,
                    "example": "Payment for invoice #001",
                },
                {
                    "name": DEBIT_COLUMN,
                    "description": "Debit amount (outgoing)",
                    "format": "Number",
                    "mandatory": False,
                    "example": "1500.00",
                },
                {
                    "name": CREDIT_COLUMN,
                    "description": "Credit amount (incoming)",
                    "format": "Number",
                    "mandatory": False,
                    "example": "2000.00",
                },
            ],
            "date_format": "YYYY-MM-DD",
            "supported_formats": ["xlsx", "csv"],
            "notes": [
                "Date, Reference, and Details are mandatory columns.",
                "Debit and Credit columns accept numbers and can be left empty.",
                "Column names are case-insensitive (e.g., 'date' matches 'Date').",
                "The same template is used for all gateways.",
            ],
        }
