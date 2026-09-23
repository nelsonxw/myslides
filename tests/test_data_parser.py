"""
Tests for data parser (CSV/Excel) (FR-4.2 Phase 2).
"""
import pytest
from myslides.generation.data_parser import DataParser


class TestDataParser:
    """Test CSV and Excel data parsing."""

    def test_parse_csv(self):
        """Test CSV parsing into chart data."""
        csv_content = """Category,Q1,Q2,Q3,Q4
Revenue,100,120,140,160
Cost,80,90,95,110
Profit,20,30,45,50"""

        result = DataParser.parse_csv(csv_content)

        assert result["categories"] == ["Q1", "Q2", "Q3", "Q4"]
        assert "Revenue" in result["series_data"]
        assert result["series_data"]["Revenue"] == [100.0, 120.0, 140.0, 160.0]
        assert "Cost" in result["series_data"]
        assert "Profit" in result["series_data"]

    def test_parse_csv_empty(self):
        """Test parsing empty CSV."""
        result = DataParser.parse_csv("")

        assert result["categories"] == []
        assert result["series_data"] == {}

    def test_parse_csv_with_invalid_values(self):
        """Test CSV with non-numeric values, negative numbers, and decimals."""
        csv_content = """Category,Q1,Q2,Q3
Revenue,100,N/A,-25.5
Cost,80,90, 42.1 """

        result = DataParser.parse_csv(csv_content)

        assert result["categories"] == ["Q1", "Q2", "Q3"]
        assert result["series_data"]["Revenue"] == [100.0, 0.0, -25.5]
        assert result["series_data"]["Cost"] == [80.0, 90.0, 42.1]

    def test_parse_excel_requires_openpyxl(self):
        """Test Excel parsing requires openpyxl and valid Excel file."""
        excel_content = b"fake excel content"

        # Should raise error for invalid Excel file
        with pytest.raises(Exception):
            DataParser.parse_excel(excel_content)
