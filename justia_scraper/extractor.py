import os
from typing import List, Optional
from firecrawl import Firecrawl
from bs4 import BeautifulSoup
from .schema import Lawyer
from dotenv import load_dotenv

load_dotenv()


class LawyerExtractor:
    """Extracts lawyer data from Justia using manual HTML parsing."""

    def __init__(self, api_key: str = None, api_url: str = None):
        """
        Initialize with Firecrawl configuration.

        Args:
            api_key: Firecrawl API key (or set FIRECRAWL_API_KEY env var)
            api_url: Custom API URL for self-hosted instances
                      (or set FIRECRAWL_API_URL env var, default: cloud API)
        """
        self.api_key = api_key or os.getenv("FIRECRAWL_API_KEY")
        if not self.api_key:
            raise ValueError(
                "FIRECRAWL_API_KEY must be provided or set in environment variables"
            )
        self.api_url = api_url or os.getenv("FIRECRAWL_API_URL")

        # Only pass api_url if it's set, to avoid Firecrawl SDK errors with None
        if self.api_url:
            self.app = Firecrawl(api_key=self.api_key, api_url=self.api_url)
        else:
            self.app = Firecrawl(api_key=self.api_key)

    def extract_from_url(self, start_url: str, max_pages: int = 5) -> List[Lawyer]:
        """
        Extract lawyer data from Justia starting URL, following pagination up to max_pages.

        Args:
            start_url: The initial Justia URL to scrape
            max_pages: Maximum number of pages to crawl (default: 5)

        Returns:
            List of Lawyer objects with extracted data
        """
        lawyers = []
        current_url = start_url
        pages_scraped = 0

        while pages_scraped < max_pages and current_url:
            print(f"Scraping page {pages_scraped + 1}: {current_url}")

            # Scrape the page to get HTML content
            try:
                scrape_result = self.app.scrape(url=current_url, formats=["html"])
            except Exception as e:
                print(f"Error scraping {current_url}: {e}")
                break

            # Extract HTML from result
            if not hasattr(scrape_result, 'html') or not scrape_result.html:
                print(f"No HTML content returned from {current_url}")
                break

            html = scrape_result.html
            page_lawyers = self._parse_lawyers_from_html(html)
            lawyers.extend(page_lawyers)

            print(f"  Found {len(page_lawyers)} lawyers on this page")

            # Find next page link
            if pages_scraped < max_pages - 1:
                current_url = self._find_next_page(html, start_url)
                if not current_url:
                    print("  No more pages found")
                    break
            else:
                break

            pages_scraped += 1

        print(f"Total lawyers extracted: {len(lawyers)}")
        return lawyers

    def _parse_lawyers_from_html(self, html: str) -> List[Lawyer]:
        """
        Parse lawyer listings from HTML content.

        Args:
            html: Raw HTML of the Justia directory page

        Returns:
            List of Lawyer objects
        """
        soup = BeautifulSoup(html, 'lxml')
        lawyers = []

        # Justia typically uses lawyer cards with specific classes
        # Start with the most specific selectors first
        lawyer_selectors = [
            'div.lawyer-card',                 # Very specific
            'div.attorney-card',
            'article.lawyer',
            'article.attorney',
            'div.listing-item',
            'div.profile-card',
            'div[itemtype*="Person"]',        # Schema.org Person markup
            'div[itemtype*="Attorney"]',
            'div.result',                     # Common for search results
            'div.search-result',
            # More general but still targeted
            'div[class*="lawyer-card"]',
            'div[class*="attorney-card"]',
            'div[class*="profile-card"]',
            'div[class*="listing"]',
        ]

        lawyer_containers = None
        for selector in lawyer_selectors:
            containers = soup.select(selector)
            if containers and len(containers) > 0:
                # Filter out obvious page-level containers (too many children)
                # A lawyer card typically has < 20 children elements
                filtered = [c for c in containers if len(c.find_all()) < 50]
                if filtered and len(filtered) > 0:
                    lawyer_containers = filtered
                    print(f"    Using selector: {selector} ({len(filtered)} elements after filtering)")
                    break

        if not lawyer_containers:
            # Fallback: look for elements that contain profile links and names
            all_candidates = soup.find_all(['div', 'article', 'li'], class_=lambda x: x and ('lawyer' in x.lower() or 'attorney' in x.lower() or 'profile' in x.lower() or 'result' in x.lower()))
            # Further filter: must contain a link to a lawyer profile page
            lawyer_containers = []
            for cand in all_candidates:
                profile_link = cand.find('a', href=lambda h: h and '/lawyers/' in h)
                name_elem = cand.find(['h3', 'h2', 'h1'], class_=lambda x: x and ('name' in x.lower() or 'title' in x.lower()))
                if profile_link and len(cand.find_all()) < 50:
                    lawyer_containers.append(cand)

            print(f"    Fallback search found {len(lawyer_containers)} potential lawyer containers")

        if not lawyer_containers:
            print("   Warning: No lawyer containers found")
            return []

        # Process each container
        for container in lawyer_containers:
            try:
                lawyer = self._parse_lawyer_from_container(container)
                if lawyer:
                    lawyers.append(lawyer)
            except Exception as e:
                print(f"Warning: Skipping lawyer container due to error: {e}")
                continue

        print(f"    Successfully parsed {len(lawyers)} lawyers from {len(lawyer_containers)} containers")
        return lawyers

    def _parse_lawyer_from_container(self, container) -> Optional[Lawyer]:
        """
        Extract lawyer data from a single container element.

        Args:
            container: BeautifulSoup element representing one lawyer listing

        Returns:
            Lawyer object or None if parsing fails
        """
        # Extract name - typically in a heading or link
        name = self._extract_name(container)
        if not name:
            # Debug: print why missing
            profile_url = self._extract_profile_url(container)
            print(f"   DEBUG: Container skipped - name='None', profile_url='{profile_url}'")
            # Show a snippet of the container HTML for debugging
            snippet = str(container)[:200]
            print(f"   Container snippet: {snippet}...")
            return None

        # Extract phone - look for phone icons, tel: links, or phone class
        phone = self._extract_phone(container)

        # Extract address - look for address tags or address class
        address = self._extract_address(container)

        # Extract profile URL - usually the first link to a profile page
        profile_url = self._extract_profile_url(container)
        if not profile_url:
            print(f"   DEBUG: Container skipped - name='{name}', profile_url='None'")
            snippet = str(container)[:200]
            print(f"   Container snippet: {snippet}...")
            return None  # Profile URL is required

        # Extract bio/experience - look for bio, experience, or description
        bio_experience = self._extract_bio(container)

        # Validate and create Lawyer object
        try:
            return Lawyer(
                Name=name,
                Phone=phone,
                Address=address,
                Profile_URL=profile_url,
                Bio_Experience=bio_experience,
            )
        except Exception as e:
            print(f"   Warning: Failed to create Lawyer for {name}: {e}")
            return None

    def _extract_text(self, container, selectors: List[str]) -> Optional[str]:
        """Try multiple selectors to extract text."""
        for selector in selectors:
            element = container.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text:
                    return text
        return None

    def _extract_phone(self, container) -> Optional[str]:
        """Extract phone number."""
        # Look for tel: links
        tel_link = container.select_one('a[href^="tel:"]')
        if tel_link:
            return tel_link['href'].replace('tel:', '').strip()

        # Look for phone class or text containing phone digits
        phone_elements = container.find_all(class_=lambda x: x and 'phone' in x.lower())
        for elem in phone_elements:
            text = elem.get_text(strip=True)
            if text and any(c.isdigit() for c in text):
                return text

        # Search for phone pattern in text
        import re
        text = container.get_text()
        phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
        if phone_match:
            return phone_match.group()

        return None

    def _extract_address(self, container) -> Optional[str]:
        """Extract address."""
        # Look for address tag
        addr_elem = container.find('address')
        if addr_elem:
            return addr_elem.get_text(strip=True)

        # Look for address class
        addr_class = container.select_one('.address, .location, .addr')
        if addr_class:
            return addr_class.get_text(strip=True)

        # Look for multiple lines that might be address (city, state pattern)
        # This is a heuristic - just return first line with city/state
        lines = container.find_all(['p', 'div', 'span'])
        for line in lines:
            text = line.get_text(strip=True)
            if text and (',' in text) and any(c.isalpha() for c in text):
                # Likely contains city, state
                return text

        return None

    def _extract_profile_url(self, container) -> Optional[str]:
        """Extract profile URL."""
        # Look for links that contain '/lawyers/' or '/attorneys/'
        links = container.find_all('a', href=True)
        for link in links:
            href = link['href']
            if '/lawyers/' in href or '/attorneys/' in href or '/profile/' in href:
                # Convert relative URLs to absolute if needed
                if href.startswith('/'):
                    href = f"https://www.justia.com{href}"
                return href
        return None

    def _extract_bio(self, container) -> Optional[str]:
        """Extract bio/experience."""
        # Look for bio, experience, or description elements
        bio_elem = container.select_one('.bio, .experience, .description, .about')
        if bio_elem:
            text = bio_elem.get_text(strip=True)
            if text:
                return text[:500]  # Limit length

        # Look for paragraphs that might be bio (exclude short ones)
        paragraphs = container.find_all('p')
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text and len(text) > 50:  # Likely a bio paragraph
                return text[:500]

        return None

    def _find_next_page(self, html: str, base_url: str) -> Optional[str]:
        """
        Find the URL of the next page.

        Args:
            html: Current page HTML
            base_url: Base URL for constructing absolute links

        Returns:
            Next page URL or None if not found
        """
        soup = BeautifulSoup(html, 'lxml')

        # Common pagination selectors
        pagination_selectors = [
            'a[rel="next"]',
            'a.next',
            'a.pagination-next',
            'li.next a',
            'a:contains("Next")',
            'a[title="Next"]',
        ]

        for selector in pagination_selectors:
            next_link = soup.select_one(selector)
            if next_link and next_link.get('href'):
                href = next_link['href']
                if href.startswith('http'):
                    return href
                elif href.startswith('/'):
                    # Construct absolute URL
                    from urllib.parse import urljoin
                    return urljoin(base_url, href)

        # Also look for "Next" text in pagination
        for link in soup.find_all('a'):
            text = link.get_text(strip=True).lower()
            if 'next' in text or '»' in text or '>' in text:
                href = link.get('href')
                if href:
                    if href.startswith('http'):
                        return href
                    elif href.startswith('/'):
                        from urllib.parse import urljoin
                        return urljoin(base_url, href)

        return None
