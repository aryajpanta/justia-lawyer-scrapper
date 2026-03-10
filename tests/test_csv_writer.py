import pytest
import csv
import tempfile
import os
from justia_scraper.csv_writer import write_lawyers_to_csv
from justia_scraper.schema import Lawyer


def test_write_lawyers_to_csv_creates_valid_csv():
    """Test that write_lawyers_to_csv creates a properly formatted CSV."""
    lawyers = [
        Lawyer(
            Name="Jane Smith",
            Phone="(555) 987-6543",
            Address="456 Oak Ave, New York, NY 10001",
            Profile_URL="https://www.justia.com/lawyers/jane-smith",
            Bio_Experience="Yale Law School",
        ),
        Lawyer(
            Name="Bob Johnson",
            Phone=None,
            Address="789 Pine St, New York, NY",
            Profile_URL="https://www.justia.com/lawyers/bob-johnson",
            Bio_Experience="Columbia Law School, 5 years",
        ),
    ]

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as tmp:
        tmp_path = tmp.name

    try:
        write_lawyers_to_csv(lawyers, output_path=tmp_path)

        # Verify file exists and is not empty
        assert os.path.exists(tmp_path)
        assert os.path.getsize(tmp_path) > 0

        # Read and verify CSV structure
        with open(tmp_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2
            assert rows[0]["Name"] == "Jane Smith"
            assert rows[0]["Phone"] == "(555) 987-6543"
            assert rows[1]["Name"] == "Bob Johnson"
            assert rows[1]["Phone"] == ""  # None becomes empty string
            assert rows[1]["Bio_Experience"] == "Columbia Law School, 5 years"
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
