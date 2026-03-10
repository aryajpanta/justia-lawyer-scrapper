#!/usr/bin/env python3
"""
Justia Lawyer Scraper - End-to-end script using Firecrawl.

This script scrapes lawyer listings from Justia, extracts structured data
(Name, Phone, Address, Profile_URL, Bio_Experience), and saves to CSV.
"""

from justia_scraper import __main__

if __name__ == "__main__":
    __main__.main()
