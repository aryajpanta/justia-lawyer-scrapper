# Justia Lawyer Scraper

Scrape lawyer listings from Justia using Firecrawl and export structured data to CSV.

## Features

- Extracts lawyer data: Name, Phone, Address, Profile URL, Bio/Experience
- Manual HTML parsing with BeautifulSoup (no LLM/AI required)
- Handles pagination automatically (up to configurable page limit)
- Works with both Firecrawl cloud API and self-hosted instances
- Outputs clean CSV with UTF-8 encoding
- Handles missing data gracefully (empty fields)

## Prerequisites

- Python 3.9+
- Firecrawl API key (get one at https://firecrawl.dev)
- pip dependencies (see `requirements.txt`)

## Installation

```bash
# Install dependencies
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

3. For self-hosted Firecrawl, also set:
   ```env
   FIRECRAWL_API_URL=http://localhost:3002
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

### Self-Hosted Firecrawl

If you're running a local Firecrawl instance:

```bash
python -m justia_scraper \
  https://www.justia.com/lawyers/immigration-law/new-york \
  --api-url http://localhost:3002 \
  --max-pages 5
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

Run integration test (requires API key and valid Firecrawl endpoint):

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
│   ├── extractor.py     # Firecrawl + BeautifulSoup scraping logic
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

1. **Scraping**: Uses Firecrawl's `/scrape` endpoint to fetch raw HTML content
   from Justia pages. This endpoint works with both cloud and self-hosted
   Firecrawl instances without any AI/LLM dependencies.

2. **Parsing**: BeautifulSoup parses the HTML and extracts lawyer data using
   intelligent CSS selectors that handle various Justia page layouts.
   The scraper finds lawyer "cards" and extracts:
   - Name (from heading or profile link)
   - Phone (from tel: links, phone classes, or regex)
   - Address (from address tags or location elements)
   - Profile URL (links to detailed lawyer pages)
   - Bio/Experience (from bio paragraphs or experience sections)

3. **Pagination**: Automatically follows "Next" page links to scrape up to
   the specified page limit.

4. **Validation**: Pydantic validates each lawyer entry against the schema,
   skipping malformed data.

5. **Export**: Python's csv module writes clean UTF-8 CSV with headers and
   proper handling of optional fields (blanks for missing data).

## Self-Hosting Firecrawl

To avoid API limits, you can self-host Firecrawl via Docker:

```bash
# Clone and set up Firecrawl
git clone https://github.com/firecrawl/firecrawl.git
cd firecrawl
cp apps/api/.env.example .env

# Configure minimum settings:
#   PORT=3002
#   HOST=0.0.0.0
#   USE_DB_AUTHENTICATION=false
#   BULL_AUTH_KEY=your_secret_here
#   (No LLM needed for scraping!)

docker compose build  # First build: 5-15 minutes
docker compose up -d

# Verify
curl http://localhost:3002/health
```

Then point the scraper to your local instance:

```bash
export FIRECRAWL_API_URL=http://localhost:3002
python -m justia_scraper --max-pages 2
```

**Note:** Unlike the `/extract` endpoint, the `/scrape` endpoint used here
**does not require an LLM**, making self-hosting lighter and simpler.

## Customizing Parsers

If Justia changes their HTML structure, you may need to update the CSS
selectors in `justia_scraper/extractor.py`. The key methods are:

- `_parse_lawyers_from_html()` - finds lawyer containers
- `_parse_lawyer_from_container()` - extracts fields from each container
- `_find_next_page()` - pagination selector

Test your changes with:

```bash
pytest tests/test_extractor.py -v
```

## Troubleshooting

**"FIRECRAWL_API_KEY must be provided"**
  → Check that your `.env` file exists and contains a valid API key.

**No lawyers extracted**
  → Verify the URL is a valid Justia lawyer directory page.
  → Try with a specific city/state combination.
  → The page structure may have changed; check if test fixtures need updating.

**API errors (429, 403, 500)**
  → For cloud API: check your Firecrawl account quota and billing.
  → For self-hosted: ensure your local Firecrawl instance is running and healthy.

**Firecrawl connection refused**
  → For self-hosted: verify `FIRECRAWL_API_URL` points to correct address.
  → Check that Docker containers are running: `docker compose ps`
  → Ensure port 3002 is accessible.
