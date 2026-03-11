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

        Strategy: Find all links to individual lawyer profiles, then locate their container elements.

        Args:
            html: Raw HTML of the Justia directory page

        Returns:
            List of Lawyer objects
        """
        soup = BeautifulSoup(html, 'lxml')
        lawyers = []

        # Find all links that point to individual lawyer profiles
        # Pattern: /lawyers/[practice-area]/[location]/[lawyer-name]/
        # Must have at least 6 segments to ensure lawyer name is present
        all_links = soup.find_all('a', href=lambda h: h and '/lawyers/' in h and len(h.split('/')) > 5)

        # Filter out non-lawyer links (cities, counties, utility pages)
        profile_links = []
        excluded_patterns = [
            'bronx', 'albany', 'kings', 'queens', 'new-york', 'manhattan',  # Common city names
            'county', 'all-cities', 'all-counties', 'show-more',  # Utility pages
            'save', 'review', 'free', 'features', 'pricing', 'about', 'contact',  # Common nav
            'login', 'signup', 'register', 'advertise', 'blog', 'news'
        ]

        for link in all_links:
            href = link.get('href', '').lower()
            # Skip if contains any excluded pattern
            if any(excluded in href for excluded in excluded_patterns):
                continue
            # Skip if the last segment is too short (<3 chars) or too long (>50)
            segments = [s for s in href.split('/') if s]
            if len(segments) < 6:
                continue
            last_segment = segments[-1]
            if len(last_segment) < 3 or len(last_segment) > 50:
                continue
            # Skip if last segment has no hyphen (single words are often cities)
            if '-' not in last_segment and last_segment.isalpha():
                continue
            profile_links.append(link)

        print(f"    Found {len(profile_links)} potential profile links (after filtering)")

        if not profile_links:
            return []

        # For each profile link, find its container (card)
        containers = []
        for link in profile_links:
            # Walk up the DOM to find a suitable container
            parent = link.find_parent(['div', 'article', 'li'])
            depth = 0
            while parent and depth < 10:
                parent_class = parent.get('class', [])
                if parent_class:
                    class_str = ' '.join(parent_class).lower()
                    # Exclude obvious non-lawyer containers
                    if any(bad in class_str for bad in ['banner', 'group', 'stripe', 'header', 'footer', 'sidebar', 'pagination', 'nav']):
                        parent = parent.find_parent(['div', 'article', 'li'])
                        depth += 1
                        continue
                    # Accept if it seems like a card (reasonable size)
                    if len(parent.find_all()) < 200:
                        containers.append(parent)
                        break
                parent = parent.find_parent(['div', 'article', 'li'])
                depth += 1

        # Deduplicate by ID or by content hash
        unique_containers = []
        seen_ids = set()
        for c in containers:
            cid = id(c)
            if cid not in seen_ids:
                unique_containers.append(c)
                seen_ids.add(cid)

        print(f"    Found {len(unique_containers)} unique lawyer containers")

        # Parse each container
        for container in unique_containers:
            try:
                lawyer = self._parse_lawyer_from_container(container)
                if lawyer:
                    lawyers.append(lawyer)
            except Exception as e:
                print(f"Warning: Skipping lawyer container due to error: {e}")
                continue

        print(f"    Successfully parsed {len(lawyers)} lawyers from {len(unique_containers)} containers")
        return lawyers

    def _parse_lawyer_from_container(self, container) -> Optional[Lawyer]:
        """
        Extract lawyer data from a single container element.

        Args:
            container: BeautifulSoup element representing one lawyer listing

        Returns:
            Lawyer object or None if parsing fails
        """
        # Extract name - typically the profile link text or heading
        name = self._extract_name(container)
        if not name:
            profile_url = self._extract_profile_url(container)
            print(f"   DEBUG: Container skipped - name='None', profile_url='{profile_url}'")
            snippet = str(container)[:200]
            print(f"   Container snippet: {snippet}...")
            return None

        # Extract phone
        phone = self._extract_phone(container)

        # Extract address
        address = self._extract_address(container)

        # Extract profile URL (required)
        profile_url = self._extract_profile_url(container)
        if not profile_url:
            print(f"   DEBUG: Container skipped - name='{name}', profile_url='None'")
            snippet = str(container)[:200]
            print(f"   Container snippet: {snippet}...")
            return None

        # Extract bio/experience
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

    def _extract_name(self, container) -> Optional[str]:
        """Extract lawyer name."""
        # Priority: profile link text, then headings, then name classes
        selectors = [
            'a[href*="/lawyers/"]',  # Profile link (most reliable)
            'h3', 'h2', 'h1', 'h4',
            '.lawyer-name', '.attorney-name', '.profile-name', '.name', '.title', '.card-title'
        ]
        return self._extract_text(container, selectors)

    def _extract_text(self, container, selectors: List[str]) -> Optional[str]:
        """Try multiple selectors to extract text."""
        for selector in selectors:
            element = container.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text and len(text) > 2:
                    # Filter out obvious non-name text
                    if any(bad in text.lower() for bad in ['privacy', 'terms', 'cookie', 'copyright']):
                        continue
                    return text
        return None

    def _extract_phone(self, container) -> Optional[str]:
        """Extract phone number."""
        # tel: links
        tel_link = container.select_one('a[href^="tel:"]')
        if tel_link:
            return tel_link['href'].replace('tel:', '').strip()

        # Phone class elements
        phone_elements = container.find_all(class_=lambda x: x and 'phone' in x.lower())
        for elem in phone_elements:
            text = elem.get_text(strip=True)
            if text and any(c.isdigit() for c in text):
                return text

        # Regex pattern
        import re
        text = container.get_text()
        phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
        if phone_match:
            return phone_match.group()

        return None

    def _extract_address(self, container) -> Optional[str]:
        """Extract address."""
        # address tag
        addr_elem = container.find('address')
        if addr_elem:
            return addr_elem.get_text(strip=True)

        # Address class
        addr_class = container.select_one('.address, .location, .addr, .street-address')
        if addr_class:
            return addr_class.get_text(strip=True)

        # Look for city/state pattern
        lines = container.find_all(['p', 'div', 'span'])
        for line in lines:
            text = line.get_text(strip=True)
            if text and ',' in text and any(c.isalpha() for c in text) and 10 < len(text) < 100:
                return text

        return None

    def _extract_profile_url(self, container) -> Optional[str]:
        """Extract profile URL."""
        links = container.find_all('a', href=True)
        for link in links:
            href = link['href']
            # Must be a lawyer profile with practice area and location in path
            if '/lawyers/' in href and len(href.split('/')) > 5:
                if href.startswith('/'):
                    href = f"https://www.justia.com{href}"
                return href
        return None

    def _extract_bio(self, container) -> Optional[str]:
        """Extract bio/experience."""
        bio_elem = container.select_one('.bio, .experience, .description, .about, .summary, .profile-bio')
        if bio_elem:
            text = bio_elem.get_text(strip=True)
            if text:
                return text[:500]

        paragraphs = container.find_all('p')
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text and 50 < len(text) < 1000:
                if any(bad in text.lower() for bad in ['privacy', 'cookie', 'terms', 'disclaimer']):
                    continue
                return text[:500]

        return None

    def _find_next_page(self, html: str, base_url: str) -> Optional[str]:
        """Find the URL of the next page."""
        soup = BeautifulSoup(html, 'lxml')

        pagination_selectors = [
            'a[rel="next"]',
            'a.next',
            'a.pagination-next',
            'li.next a',
            'a[title="Next"]',
            'a[aria-label="Next"]',
            'a:-soup-contains("Next")',
            'a:-soup-contains(">")',
            'a:-soup-contains("»")',
        ]

        for selector in pagination_selectors:
            try:
                next_link = soup.select_one(selector)
                if next_link and next_link.get('href'):
                    href = next_link['href']
                    if href.startswith('http'):
                        return href
                    elif href.startswith('/'):
                        from urllib.parse import urljoin
                        return urljoin(base_url, href)
            except Exception:
                continue

        for link in soup.find_all('a'):
            text = link.get_text(strip=True).lower()
            if 'next' in text or '»' in text or '>' in text or '→' in text:
                href = link.get('href')
                if href:
                    if href.startswith('http'):
                        return href
                    elif href.startswith('/'):
                        from urllib.parse import urljoin
                        return urljoin(base_url, href)

        return None
