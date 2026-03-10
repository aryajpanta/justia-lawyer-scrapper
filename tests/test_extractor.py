import pytest
from unittest.mock import Mock, patch, MagicMock
from justia_scraper.extractor import LawyerExtractor
from justia_scraper.schema import Lawyer


# Sample HTML for Justia lawyer listing page (simplified)
SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<body>
<div class="lawyer-card">
    <h3><a href="/lawyers/john-doe/">John Doe</a></h3>
    <div class="phone"><a href="tel:(555)123-4567">(555) 123-4567</a></div>
    <div class="address">123 Main St, New York, NY 10001</div>
    <div class="bio">Harvard Law School, 10 years experience in immigration law.</div>
    <a href="/lawyers/john-doe/">View Profile</a>
</div>
<div class="lawyer-card">
    <h3><a href="/lawyers/jane-smith/">Jane Smith</a></h3>
    <div class="phone">(555) 987-6543</div>
    <div class="address">456 Oak Ave, New York, NY</div>
    <div class="bio">Yale Law School graduate.</div>
    <a href="/lawyers/jane-smith/">Profile</a>
</div>
</body>
</html>
"""


HTML_WITH_NEXT_PAGE = """
<!DOCTYPE html>
<html>
<body>
<div class="lawyer-card">
    <h3><a href="/lawyers/attorney-one/">Attorney One</a></h3>
    <div class="phone">555-111-2222</div>
    <div class="address">123 Test St</div>
    <div class="bio">Test bio information.</div>
</div>
</body>
<div class="pagination">
    <a href="/lawyers/immigration-law/new-york/page-2/">Next</a>
</div>
</html>
"""


def test_extract_lawyers_returns_list_of_lawyer_objects():
    """Test that extract_from_url returns a list of Lawyer instances."""
    extractor = LawyerExtractor(api_key="test-key")

    # Mock the Firecrawl scrape method
    mock_result = Mock()
    mock_result.html = SAMPLE_HTML

    with patch.object(extractor.app, 'scrape', return_value=mock_result):
        lawyers = extractor.extract_from_url("https://www.justia.com/test", max_pages=1)

    assert isinstance(lawyers, list)
    assert len(lawyers) >= 1  # At least one lawyer extracted
    assert all(isinstance(l, Lawyer) for l in lawyers)
    # Verify some data
    assert any(l.Name == "John Doe" or l.Name == "Jane Smith" for l in lawyers)


def test_extract_lawyers_handles_empty_results():
    """Test that extractor handles pages with no lawyers gracefully."""
    extractor = LawyerExtractor(api_key="test-key")

    empty_html = "<html><body>No lawyer listings</body></html>"
    mock_result = Mock()
    mock_result.html = empty_html

    with patch.object(extractor.app, 'scrape', return_value=mock_result):
        lawyers = extractor.extract_from_url("https://www.justia.com/test", max_pages=1)

    assert lawyers == []


def test_extractor_initializes_with_api_url():
    """Test that extractor accepts and uses custom api_url."""
    with patch("justia_scraper.extractor.Firecrawl") as mock_firecrawl:
        mock_firecrawl.return_value = MagicMock()
        mock_firecrawl.return_value.scrape = MagicMock(return_value=Mock(html=""))

        extractor = LawyerExtractor(api_key="test-key", api_url="http://localhost:3002")

        mock_firecrawl.assert_called_once_with(api_key="test-key", api_url="http://localhost:3002")
        assert extractor.api_url == "http://localhost:3002"


def test_extractor_uses_env_api_url():
    """Test that extractor reads FIRECRAWL_API_URL from environment."""
    with patch("justia_scraper.extractor.Firecrawl") as mock_firecrawl, \
         patch.dict("os.environ", {"FIRECRAWL_API_URL": "http://localhost:3002"}):
        mock_firecrawl.return_value = MagicMock()
        mock_firecrawl.return_value.scrape = MagicMock(return_value=Mock(html=""))

        extractor = LawyerExtractor(api_key="test-key")

        mock_firecrawl.assert_called_once_with(api_key="test-key", api_url="http://localhost:3002")
        assert extractor.api_url == "http://localhost:3002"


def test_extract_with_pagination():
    """Test that scraper follows pagination correctly."""
    extractor = LawyerExtractor(api_key="test-key")

    # First page returns lawyers and a next link
    mock_result_page1 = Mock()
    mock_result_page1.html = HTML_WITH_NEXT_PAGE

    # Second page returns lawyers but no next link
    html_page2 = """
    <!DOCTYPE html>
    <html>
    <body>
    <div class="lawyer-card">
        <h3><a href="/lawyers/attorney-two/">Attorney Two</a></h3>
        <div class="phone">555-333-4444</div>
        <div class="address">789 Pine St</div>
        <div class="bio">Second page bio.</div>
    </div>
    </body>
    </html>
    """
    mock_result_page2 = Mock()
    mock_result_page2.html = html_page2

    # Mock scrape to return different results on each call
    scrape_calls = []
    def mock_scrape(url, formats):
        scrape_calls.append(url)
        if 'page-2' in url:
            return mock_result_page2
        return mock_result_page1

    with patch.object(extractor.app, 'scrape', side_effect=mock_scrape):
        lawyers = extractor.extract_from_url("https://www.justia.com/test", max_pages=3)

    assert len(lawyers) == 2  # One from page 1, one from page 2
    assert any(l.Name == "Attorney One" for l in lawyers)
    assert any(l.Name == "Attorney Two" for l in lawyers)
    assert len(scrape_calls) == 2  # Should have stopped after page 2
