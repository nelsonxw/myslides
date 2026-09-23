"""
Data Parser for CSV and Excel file uploads (FR-4.2 Phase 2).
Parses uploaded files into chart-ready data structures.
"""
from typing import Dict, List, Any, Optional
import csv
from io import StringIO


class DataParser:
    """Parses CSV and Excel files into chart data."""

    @staticmethod
    def parse_csv(csv_content: str) -> Dict[str, Any]:
        """
        Parse CSV content into chart data.

        Args:
            csv_content: CSV file content as string

        Returns:
            Dictionary with categories and series_data
        """
        reader = csv.reader(StringIO(csv_content))
        rows = list(reader)

        if not rows:
            return {"categories": [], "series_data": {}}

        # First row is categories (header)
        categories = rows[0][1:] if len(rows[0]) > 1 else []

        # Subsequent rows are series data
        series_data = {}
        for row in rows[1:]:
            if not row:
                continue
            series_name = str(row[0]).strip() if row[0] else f"Series {len(series_data) + 1}"
            values = []
            for v in row[1:]:
                try:
                    values.append(float(str(v).strip()))
                except (ValueError, TypeError):
                    values.append(0.0)
            series_data[series_name] = values

        return {
            "categories": categories,
            "series_data": series_data
        }

    @staticmethod
    def parse_excel(excel_content: bytes) -> Dict[str, Any]:
        """
        Parse Excel file content into chart data.

        Args:
            excel_content: Excel file content as bytes

        Returns:
            Dictionary with categories and series_data
        """
        try:
            import openpyxl
            from io import BytesIO

            workbook = openpyxl.load_workbook(BytesIO(excel_content))
            sheet = workbook.active

            rows = []
            for row in sheet.iter_rows(values_only=True):
                rows.append([cell for cell in row if cell is not None])

            if not rows:
                return {"categories": [], "series_data": {}}

            # First row is categories (header)
            categories = [str(r).strip() for r in rows[0][1:]] if len(rows[0]) > 1 else []

            # Subsequent rows are series data
            series_data = {}
            for row in rows[1:]:
                if not row:
                    continue
                series_name = str(row[0]).strip() if row[0] else f"Series {len(series_data) + 1}"
                values = []
                for v in row[1:]:
                    try:
                        values.append(float(v))
                    except (ValueError, TypeError):
                        values.append(0.0)
                series_data[series_name] = values

            return {
                "categories": categories,
                "series_data": series_data
            }
        except ImportError:
            raise ImportError("openpyxl is required for Excel parsing. Install with: pip install openpyxl")
        except Exception as e:
            raise ValueError(f"Failed to parse Excel file: {e}")
