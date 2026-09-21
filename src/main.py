import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
URL = "https://books.toscrape.com/"
HEADERS = {
    "User-Agent": "FlyRankInternshipA9/1.0 ([https://github.com/Red-swipe/Flyrank_project-5](https://github.com/Red-swipe/Flyrank_project-5))"
}


def utc_timestamp():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_page(url, cache_file):
    if cache_file.exists():
        content = cache_file.read_bytes()
        print("CACHE HIT")
        return content, utc_timestamp()

    time.sleep(0.6)
    fetched_at = utc_timestamp()
    response = requests.get(url, headers=HEADERS, timeout=10)
    if response.status_code != 200:
        print(f"ERROR: received status code {response.status_code}")
        raise SystemExit(1)

    content = response.content
    cache_file.write_bytes(content)
    print("FETCH")
    return content, fetched_at


def parse_html(content):
    return BeautifulSoup(content.decode("utf-8"), "html.parser")


page_urls = [URL]
page_contents = []

for page_number in range(1, 4):
    page_url = page_urls[-1]
    cache_file = CACHE_DIR / f"catalogue-page-{page_number}.html"
    content, _ = load_page(page_url, cache_file)
    source_page = urljoin(URL, f"catalogue/page-{page_number}.html")
    page_contents.append((page_url, source_page, content))

    if page_number < 3:
        soup = parse_html(content)
        next_link = soup.select_one("li.next a[href]")
        if next_link is None:
            print("ERROR: next page link not found")
            raise SystemExit(1)
        page_urls.append(urljoin(page_url, next_link["href"]))


books = []
for page_url, source_page, content in page_contents:
    soup = parse_html(content)
    for link in soup.select("article.product_pod h3 a[href]"):
        books.append({
            "product_url": urljoin(page_url, link["href"]),
            "source_page": source_page,
        })


records = []
for book in books:
    product_url = book["product_url"]
    cache_name = hashlib.sha256(product_url.encode("utf-8")).hexdigest()
    detail_cache = CACHE_DIR / f"detail-{cache_name}.html"
    content, fetched_at = load_page(product_url, detail_cache)

    soup = parse_html(content)
    product_area = soup.select_one("div.product_main")
    if product_area is None:
        print(f"ERROR: product area not found for {product_url}")
        raise SystemExit(1)

    title = product_area.select_one("h1")
    price = product_area.select_one("p.price_color")
    availability = product_area.select_one("p.instock.availability")
    rating = product_area.select_one("p.star-rating")

    description = None
    description_heading = soup.select_one("#product_description")
    if description_heading is not None:
        description_element = description_heading.find_next_sibling("p")
        if description_element is not None:
            description = description_element.get_text(strip=True)

    rating_text = None
    if rating is not None:
        rating_classes = [name for name in rating.get("class", []) if name != "star-rating"]
        rating_text = rating_classes[0] if rating_classes else None

    records.append({
        "title": title.get_text(strip=True) if title else None,
        "product_url": product_url,
        "price_text": price.get_text(strip=True) if price else None,
        "availability_text": availability.get_text(" ", strip=True) if availability else None,
        "rating_text": rating_text,
        "description": description,
        "source_page": book["source_page"],
        "fetched_at": fetched_at,
    })


unique_urls = {book["product_url"] for book in books}
if len(unique_urls) != 60:
    print(f"ERROR: expected 60 unique book URLs, found {len(unique_urls)}")
    raise SystemExit(1)

print(json.dumps(records[0], indent=2, ensure_ascii=False))
print(f"detail_pages={len(records)}")
