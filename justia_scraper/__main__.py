#!/usr/bin/env python3
"""
End-to-end script to scrape Justia lawyer listings and export to CSV.

Usage:
    python -m justia_scraper [URL] [--max-pages N] [--output FILE]

Example:
    python -m justia_scraper https://www.justia.com/lawyers/immigration-law/new-york --max-pages 5
"""
import argparse
import sys
from .extractor import LawyerExtractor
from .csv_writer import write_lawyers_to_csv


def main():
    parser = argparse.ArgumentParser(
        description="Scrape lawyer listings from Justia and export to CSV"
    )
    parser.add_argument(
        "url",
        nargs="?",
        default="https://www.justia.com/lawyers/immigration-law/new-york",
        help="Justia URL to scrape (default: immigration lawyers in New York)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=5,
        help="Maximum number of pages to scrape (default: 5)",
    )
    parser.add_argument(
        "--output",
        default="immigration_lawyers.csv",
        help="Output CSV file path (default: immigration_lawyers.csv)",
    )

    args = parser.parse_args()

    try:
        print(f"Starting extraction from: {args.url}")
        print(f"Max pages: {args.max_pages}")

        extractor = LawyerExtractor()
        lawyers = extractor.extract_from_url(
            start_url=args.url, max_pages=args.max_pages
        )

        print(f"Extracted {len(lawyers)} lawyers")

        if lawyers:
            write_lawyers_to_csv(lawyers, output_path=args.output)
            print(f"✓ Data saved to {args.output}")
        else:
            print("Warning: No lawyer data extracted")
            sys.exit(1)

    except ValueError as e:
        print(f"Error: {e}")
        print(
            "Make sure FIRECRAWL_API_KEY is set in your environment or .env file"
        )
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
