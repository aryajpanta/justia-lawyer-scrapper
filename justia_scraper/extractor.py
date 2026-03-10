import os
from typing import List
from firecrawl import Firecrawl
from .schema import Lawyer
from dotenv import load_dotenv

load_dotenv()


class LawyerExtractor:
    """Extracts lawyer data from Justia using Firecrawl."""

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
        # Note: Firecrawl's FIRE-1 agent handles pagination automatically.
        # The max_pages parameter serves as a conceptual limit; actual pagination
        # behavior depends on Firecrawl's internal implementation.
        schema = Lawyer.model_json_schema()

        extraction_result = self.app.extract(
            urls=[start_url],
            prompt="""
            Extract ALL lawyer listings from this page.
            For each lawyer, find:
            - Their full name (Name)
            - Phone number (Phone) - may be in 'Call' button or contact section
            - Office address (Address) - look for address near their name
            - Profile URL (Profile_URL) - link to their Justia profile page
            - Bio/Experience (Bio_Experience) - law school, years experience, or practice description

            Return an array of lawyer objects. Follow pagination links to next pages up to the page limit.
            """,
            schema={
                "type": "object",
                "properties": {
                    "lawyers": {
                        "type": "array",
                        "items": schema
                    }
                },
                "required": ["lawyers"]
            }
            # Note: agent parameter is cloud-only (FIRE-1). Self-hosted uses
            # the configured LLM (OpenAI/Ollama) without explicit agent.
        )

        # Extract the lawyers array from the result
        if not extraction_result.data:
            return []

        # The result structure: data[0].content contains the extracted lawyers
        first_result = extraction_result.data[0]
        content = first_result.content if hasattr(first_result, 'content') else first_result

        if isinstance(content, dict) and 'lawyers' in content:
            lawyers_data = content['lawyers']
        else:
            # If the schema wasn't wrapped, assume the content is the list
            lawyers_data = content if isinstance(content, list) else []

        # Convert to Lawyer objects, skipping invalid entries
        lawyers = []
        for item in lawyers_data:
            try:
                lawyer = Lawyer(**item)
                lawyers.append(lawyer)
            except Exception as e:
                print(f"Warning: Skipping invalid lawyer data: {e}")
                continue

        return lawyers
