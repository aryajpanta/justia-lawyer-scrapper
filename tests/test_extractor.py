import pytest
from unittest.mock import Mock, patch
from justia_scraper.extractor import LawyerExtractor
from justia_scraper.schema import Lawyer


def test_extract_lawyers_returns_list_of_lawyer_objects():
    """Test that extract_from_url returns a list of Lawyer instances."""
    extractor = LawyerExtractor(api_key="test-key")

    # Mock the Firecrawl app.extract method
    mock_result = Mock()
    mock_result.data = [
        Mock(
            content={
                "lawyers": [
                    {
                        "Name": "John Doe",
                        "Phone": "(555) 123-4567",
                        "Address": "123 Main St, New York, NY",
                        "Profile_URL": "https://www.justia.com/lawyers/john-doe",
                        "Bio_Experience": "Harvard Law School, 10 years experience",
                    }
                ]
            }
        )
    ]

    with patch.object(extractor.app, "extract", return_value=mock_result):
        lawyers = extractor.extract_from_url("https://www.justia.com/test", max_pages=1)

    assert isinstance(lawyers, list)
    assert len(lawyers) == 1
    assert isinstance(lawyers[0], Lawyer)
    assert lawyers[0].Name == "John Doe"


def test_extract_lawyers_handles_empty_results():
    """Test that extractor handles pages with no lawyers gracefully."""
    extractor = LawyerExtractor(api_key="test-key")

    mock_result = Mock()
    mock_result.data = [Mock(content={})]

    with patch.object(extractor.app, "extract", return_value=mock_result):
        lawyers = extractor.extract_from_url("https://www.justia.com/test", max_pages=1)

    assert lawyers == []
