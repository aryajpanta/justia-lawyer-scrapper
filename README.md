# Justia Lawyer Scraper

Scrape lawyer listings from Justia using Firecrawl and export structured data to CSV.

## Features

- Extracts lawyer data: Name, Phone, Address, Profile URL, Bio/Experience
- Handles pagination automatically (up to configurable page limit)
- Uses Firecrawl's FIRE-1 agent for reliable extraction
- Outputs clean CSV with UTF-8 encoding
- Handles missing data gracefully (empty fields)

## Prerequisites

- Python 3.9+
- Firecrawl API key (get one at https://firecrawl.dev)
- pip dependencies (see `requirements.txt`)

## Installation

```bash
# Clone and install dependencies
pip install -r requirements.txt
```

## Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Firecrawl API key:
   ```env
   FIRECRAWL_API_KEY=fc-your_key_here
   ```

## Usage

### Basic usage (default URL):

```bash
python -m justia_scraper
```

This scrapes immigration lawyers in New York, up to 5 pages, and saves to `immigration_lawyers.csv`.

### Custom URL:

```bash
python -m justia_scraper https://www.justia.com/lawyers/family-law/california
```

### Adjust page limit:

```bash
python -m justia_scraper --max-pages 3
```

### Custom output file:

```bash
python -m justia_scraper --output my_lawyers.csv
```

### All options together:

```bash
python -m justia_scraper \
  https://www.justia.com/lawyers/employment-law/texas \
  --max-pages 2 \
  --output texas_employment_lawyers.csv
```

## Output CSV Format

The CSV contains these columns:

| Column | Description |
|--------|-------------|
| Name | Lawyer's full name |
| Phone | Contact phone number (may be blank) |
| Address | Office address (may be blank) |
| Profile_URL | Link to Justia profile |
| Bio_Experience | Bio text, law school, experience |

## Testing

Run the test suite:

```bash
pytest tests/ -v
```

Run integration test (requires API key):

```bash
FIRECRAWL_API_KEY=your_key pytest tests/test_integration.py -v
```

## Project Structure

```
.
├── justia_scraper/
│   ├── __init__.py
│   ├── __main__.py      # CLI entry point
│   ├── schema.py        # Pydantic Lawyer model
│   ├── extractor.py     # Firecrawl extraction logic
│   └── csv_writer.py    # CSV export functionality
├── tests/
│   ├── test_extractor.py
│   ├── test_csv_writer.py
│   └── test_integration.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── scrape_justia.py     # Top-level runner
```

## How It Works

1. **Extraction**: Uses Firecrawl's `/v1/extract` endpoint with the FIRE-1 agent.
   The agent navigates pagination automatically and extracts structured data
   according to the provided schema.

2. **Validation**: Pydantic validates each lawyer entry against the schema,
   skipping malformed data.

3. **Export**: Python's csv module writes clean UTF-8 CSV with headers and
   proper handling of optional fields (blanks for missing data).

## Troubleshooting

**"FIRECRAWL_API_KEY must be provided"**
  → Check that your `.env` file exists and contains a valid API key.

**No lawyers extracted**
  → Verify the URL is a valid Justia lawyer directory page.
  → Try with a specific city/state combination.

**API errors**
  → Check your Firecrawl account quota and billing status.
```
