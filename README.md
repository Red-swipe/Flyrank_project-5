# The Polite Scraper

## Target Classification

- Target site: books.toscrape.com
- Scope: first 3 catalogue pages only, 60 books total
- Data collected: title, price, availability, rating, description, product URL
- Why it's appropriate: It is a public demo website specifically designed for web scraping practice.
- Robots.txt result: Not accessible for verification at the time of writing; verify before scraping.
- I will not reuse this code on another site without checking its rules and terms first.

## How to run

```bash
pip install requests beautifulsoup4 pydantic
python src/main.py
```

## What it collects

| Field | Type |
|---|---|
| `title` | `str` |
| `product_url` | `HttpUrl` |
| `price_text` | `str` |
| `price_gbp` | `float` |
| `availability_text` | `str` |
| `rating_text` | `str` |
| `description` | `str | None` |
| `source_page` | `str` |
| `fetched_at` | `str` |

## Politeness rules

- Uses an honest user-agent.
- Waits 600ms between requests.
- Uses a 10-second timeout.
- Caches pages during development.

## Sample run report

```json
{
  "start_time": "2026-09-21T15:24:22Z",
  "duration_seconds": 3.274,
  "catalogue_pages_fetched": 0,
  "cache_hits": 63,
  "detail_pages_fetched": 0,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": [
    "https://books.toscrape.com/catalogue/this-book-does-not-exist_9999/index.html"
  ]
}
```

## Why no browser was needed

The data is already in the static HTML the server sends, so a browser would only add overhead.

## Limitation

The scraper is intentionally limited to the first 3 catalogue pages (60 books) and depends on the current HTML structure of books.toscrape.com; changes to that structure may require selector updates.

## Ethics Note

- Use official APIs when they exist.
- Never bypass logins or paywalls.
- Collect only what you need.
