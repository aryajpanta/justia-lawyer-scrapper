import pytest
import os
from justia_scraper.extractor import LawyerExtractor


@pytest.mark.skipif(
    not os.getenv("FIRECRAWL_API_KEY"),
    reason="FIRECRAWL_API_KEY not set",
)
def test_full_integration_creates_csv():
    """Integration test: extract and write CSV (requires API key)."""
    from justia_scraper.csv_writer import write_lawyers_to_csv
    import tempfile

    extractor = LawyerExtractor()
    lawyers = extractor.extract_from_url(
        "https://www.justia.com/lawyers/immigration-law/new-york",
        max_pages=1,
    )

    assert len(lawyers) > 0

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as tmp:
        tmp_path = tmp.name

    try:
        write_lawyers_to_csv(lawyers, output_path=tmp_path)
        assert os.path.exists(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
