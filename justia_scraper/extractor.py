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

        if self.api_url:
            self.app = Firecrawl(api_key=self.api_key, api_url=self.api_url)
        else:
            self.app = Firecrawl(api_key=self.api_key)

    def extract_from_url(self, start_url: str, max_pages: int = 5) -> List[Lawyer]:
        """Extract lawyer data from Justia with pagination."""
        lawyers = []
        current_url = start_url
        pages_scraped = 0

        while pages_scraped < max_pages and current_url:
            print(f"Scraping page {pages_scraped + 1}: {current_url}")

            try:
                scrape_result = self.app.scrape(url=current_url, formats=["html"])
            except Exception as e:
                print(f"Error scraping {current_url}: {e}")
                break

            if not hasattr(scrape_result, 'html') or not scrape_result.html:
                print(f"No HTML content returned from {current_url}")
                break

            html = scrape_result.html
            page_lawyers = self._parse_lawyers_from_html(html)
            lawyers.extend(page_lawyers)

            print(f"  Found {len(page_lawyers)} lawyers on this page")

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
        Parse lawyer listings using structural heuristics to find individual profile cards.

        Strategy: Find elements that contain both a profile link AND a name-like heading,
        while excluding common non-lawyer containers.
        """
        soup = BeautifulSoup(html, 'lxml')
        lawyers = []

        # Look for divs/articles that contain:
        # - A link to a lawyer profile (href with /lawyers/ and lawyer-name pattern)
        # - A heading (h2, h3) that looks like a person's name
        candidate_containers = soup.find_all(['div', 'article', 'li'])

        print(f"    Checking {len(candidate_containers)} potential containers")

        for container in candidate_containers:
            # Skip if container is inside a sidebar, header, footer, or nav
            parent_classes = []
            parent = container
            for _ in range(3):
                if parent is None:
                    break
                parent = parent.find_parent(['div', 'nav', 'header', 'footer', 'aside'])
                if parent:
                    cls = parent.get('class', [])
                    if cls:
                        parent_classes.extend(cls)
            if parent_classes:
                skip_parent = any(x in ' '.join(parent_classes).lower() for x in ['sidebar', 'nav', 'header', 'footer', 'pagination', 'menu'])
                if skip_parent:
                    continue

            # Check if this container has a valid profile link
            profile_link = None
            links = container.find_all('a', href=True)
            for link in links:
                href = link.get('href', '').lower()
                if '/lawyers/' not in href:
                    continue
                segments = [s for s in href.split('/') if s]
                if len(segments) < 6:
                    continue
                last_seg = segments[-1]
                # Profile link characteristics:
                # - last segment is hyphenated OR long (>=8 chars) AND not a known city/county
                # - NOT a utility page
                city_county_terms = ['bronx', 'brooklyn', 'queens', 'manhattan', 'staten-island',
                                    'new-york', 'albany', 'erie', 'monroe', 'westchester',
                                    'county', 'cities', 'counties', 'all-cities', 'all-counties',
                                    'legal-aid', 'pro-bono', 'services', 'society', 'organization',
                                    'firm', 'group', 'show-more', 'save', 'review']
                if last_seg in city_county_terms:
                    continue
                if any(term in last_seg for term in ['legal-aid', 'pro-bono', 'services']):
                    continue
                if len(last_seg) < 6 and last_seg.isalpha() and '-' not in last_seg:
                    continue
                if '-' in last_seg or len(last_seg) >= 8:
                    profile_link = link
                    break

            if not profile_link:
                continue

            # Check if container has a heading that looks like a person's name
            name = None
            heading = container.find(['h1', 'h2', 'h3', 'h4'])
            if heading:
                heading_text = heading.get_text(strip=True)
                if heading_text and 5 < len(heading_text) < 100:
                    # Basic name heuristics:
                    # - Contains at least 2 words (first + last)
                    # - Not all uppercase (avoidy headings like "FEATURED ATTORNEYS")
                    # - Contains letters only (mostly)
                    words = heading_text.split()
                    if len(words) >= 2:
                        if not heading_text.isupper():
                            name = heading_text

            # Also check if the profile link text itself looks like a name
            if not name:
                link_text = profile_link.get_text(strip=True)
                if link_text and 5 < len(link_text) < 100:
                    words = link_text.split()
                    if len(words) >= 2 and not link_text.isupper():
                        name = link_text

            if not name:
                continue

            # This container looks like a lawyer card!
            # Extract other fields
            phone = self._extract_phone(container)
            address = self._extract_address(container)
            profile_url = profile_link.get('href')
            if profile_url.startswith('/'):
                profile_url = f"https://www.justia.com{profile_url}"
            bio_experience = self._extract_bio(container)

            try:
                lawyer = Lawyer(
                    Name=name,
                    Phone=phone,
                    Address=address,
                    Profile_URL=profile_url,
                    Bio_Experience=bio_experience,
                )
                lawyers.append(lawyer)
            except Exception as e:
                print(f"   Warning: Failed to create Lawyer for {name}: {e}")
                continue

        print(f"    Successfully parsed {len(lawyers)} lawyers")
        return lawyers

    def _extract_phone(self, container) -> Optional[str]:
        """Extract phone number."""
        tel_link = container.select_one('a[href^="tel:"]')
        if tel_link:
            return tel_link['href'].replace('tel:', '').strip()

        phone_elements = container.find_all(class_=lambda x: x and 'phone' in x.lower())
        for elem in phone_elements:
            text = elem.get_text(strip=True)
            if text and any(c.isdigit() for c in text):
                return text

        import re
        text = container.get_text()
        phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
        if phone_match:
            return phone_match.group()

        return None

    def _extract_address(self, container) -> Optional[str]:
        """Extract address."""
        addr_elem = container.find('address')
        if addr_elem:
            return addr_elem.get_text(strip=True)

        addr_class = container.select_one('.address, .location, .addr, .street-address')
        if addr_class:
            return addr_class.get_text(strip=True)

        lines = container.find_all(['p', 'div', 'span'])
        for line in lines:
            text = line.get_text(strip=True)
            if text and ',' in text and any(c.isalpha() for c in text) and 10 < len(text) < 100:
                return text

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
