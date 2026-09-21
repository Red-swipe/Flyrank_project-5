import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl, ValidationError


BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
OUTPUT_DIR = BASE_DIR / "output"
BOOKS_FILE = OUTPUT_DIR / "books.json"
ERRORS_FILE = OUTPUT_DIR / "errors.json"
REPORT_FILE = OUTPUT_DIR / "run-report.json"
URL = "https://books.toscrape.com/"
HEADERS = {
    "User-Agent": "FlyRankInternshipA9/1.0 ([https://github.com/Red-swipe/Flyrank_project-5](https://github.com/Red-swipe/Flyrank_project-5))"
}

stats = {
    "catalogue_pages_fetched": 0,
    "cache_hits": 0,
    "detail_pages_fetched": 0,
}
failed_pages = []
run_start = datetime.now(timezone.utc)
run_started_at = time.perf_counter()


class BookRecord(BaseModel):
    title: str
    product_url: HttpUrl
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str
    description: str | None
    source_page: str
    fetched_at: str


def utc_timestamp():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_page(url, cache_file):
    if cache_file.exists():
        stats["cache_hits"] += 1
        content = cache_file.read_bytes()
        print("CACHE HIT")
        return content, utc_timestamp()

    time.sleep(0.6)
    fetched_at = utc_timestamp()
    response = requests.get(url, headers=HEADERS, timeout=10)
    if response.status_code != 200:
        print(f"ERROR: received status code {response.status_code}")
        raise RuntimeError(f"HTTP {response.status_code}")

    content = response.content
    cache_file.write_bytes(content)
    stats["catalogue_pages_fetched"] += 1
    print("FETCH")
    return content, fetched_at


def load_detail_page(url, cache_file):
    if cache_file.exists():
        stats["cache_hits"] += 1
        content = cache_file.read_bytes()
        print("CACHE HIT")
        return content, utc_timestamp()

    for attempt in range(2):
        time.sleep(0.6)
        fetched_at = utc_timestamp()
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
        except requests.exceptions.Timeout as exc:
            if attempt == 0:
                time.sleep(2)
                continue
            raise RuntimeError("request timed out after retry") from exc
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"request failed: {exc}") from exc

        if response.status_code == 200:
            content = response.content
            cache_file.write_bytes(content)
            stats["detail_pages_fetched"] += 1
            print("FETCH")
            return content, fetched_at

        if response.status_code in (403, 404):
            raise RuntimeError(f"HTTP {response.status_code}")

        if 500 <= response.status_code <= 599 and attempt == 0:
            time.sleep(2)
            continue

        raise RuntimeError(f"HTTP {response.status_code}")

    raise RuntimeError("request failed after retry")


def parse_html(content):
    return BeautifulSoup(content.decode("utf-8"), "html.parser")


def normalize_record(raw_record):
    price_gbp = float(raw_record["price_text"].replace("£", "").strip())
    return {
        **raw_record,
        "price_gbp": price_gbp,
    }


def validate_record(record):
    validated = BookRecord.model_validate(record)
    return validated.model_dump(mode="json")


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
            raise RuntimeError("next page link not found")
        page_urls.append(urljoin(page_url, next_link["href"]))


books = []
for page_url, source_page, content in page_contents:
    soup = parse_html(content)
    for link in soup.select("article.product_pod h3 a[href]"):
        books.append({
            "product_url": urljoin(page_url, link["href"]),
            "source_page": source_page,
        })

books.append({
    "product_url": "https://books.toscrape.com/catalogue/this-book-does-not-exist_9999/index.html",
    "source_page": urljoin(URL, "catalogue/page-1.html"),
})


raw_records = []
for book in books:
    product_url = book["product_url"]
    cache_name = hashlib.sha256(product_url.encode("utf-8")).hexdigest()
    detail_cache = CACHE_DIR / f"detail-{cache_name}.html"

    try:
        content, fetched_at = load_detail_page(product_url, detail_cache)
        soup = parse_html(content)
        product_area = soup.select_one("div.product_main")
        if product_area is None:
            raise RuntimeError("product area not found")

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

        raw_records.append({
            "title": title.get_text(strip=True) if title else None,
            "product_url": product_url,
            "price_text": price.get_text(strip=True) if price else None,
            "availability_text": availability.get_text(" ", strip=True) if availability else None,
            "rating_text": rating_text,
            "description": description,
            "source_page": book["source_page"],
            "fetched_at": fetched_at,
        })
    except Exception as exc:
        reason = str(exc)
        failed_pages.append(product_url)
        print(f"FAILURE: {product_url} - {reason}")


good_by_url = {}
errors = []

if BOOKS_FILE.exists():
    existing_records = json.loads(BOOKS_FILE.read_text(encoding="utf-8"))
    for existing_record in existing_records:
        try:
            validated_record = validate_record(existing_record)
            good_by_url[str(validated_record["product_url"])] = validated_record
        except ValidationError as exc:
            errors.append({"record": existing_record, "reason": str(exc)})

for raw_record in raw_records:
    try:
        normalized_record = normalize_record(raw_record)
        validated_record = validate_record(normalized_record)
        good_by_url[str(validated_record["product_url"])] = validated_record
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        errors.append({"record": raw_record, "reason": str(exc)})


good_records = list(good_by_url.values())
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
BOOKS_FILE.write_text(json.dumps(good_records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
ERRORS_FILE.write_text(json.dumps(errors, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

run_report = {
    "start_time": run_start.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "duration_seconds": round(time.perf_counter() - run_started_at, 3),
    "catalogue_pages_fetched": stats["catalogue_pages_fetched"],
    "cache_hits": stats["cache_hits"],
    "detail_pages_fetched": stats["detail_pages_fetched"],
    "valid_records": len(good_records),
    "invalid_records": len(errors),
    "failed_pages": failed_pages,
}
REPORT_FILE.write_text(json.dumps(run_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

print(f"valid={len(good_records)} invalid={len(errors)}")
