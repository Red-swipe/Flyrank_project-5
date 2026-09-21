import time
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


def load_page(url, cache_file):
    if cache_file.exists():
        content = cache_file.read_bytes()
        print("CACHE HIT")
        return content

    time.sleep(0.6)
    response = requests.get(url, headers=HEADERS, timeout=10)
    if response.status_code != 200:
        print(f"ERROR: received status code {response.status_code}")
        raise SystemExit(1)

    content = response.content
    cache_file.write_bytes(content)
    print("FETCH")
    return content


page_urls = [URL]
page_contents = []

for page_number in range(1, 4):
    page_url = page_urls[-1]
    cache_file = CACHE_DIR / f"catalogue-page-{page_number}.html"
    content = load_page(page_url, cache_file)
    page_contents.append((page_url, content))

    if page_number < 3:
        soup = BeautifulSoup(content, "html.parser")
        next_link = soup.select_one("li.next a[href]")
        if next_link is None:
            print("ERROR: next page link not found")
            raise SystemExit(1)
        page_urls.append(urljoin(page_url, next_link["href"]))


book_urls = []
for page_url, content in page_contents:
    soup = BeautifulSoup(content, "html.parser")
    for link in soup.select("article.product_pod h3 a[href]"):
        book_urls.append(urljoin(page_url, link["href"]))

unique_urls = set(book_urls)
print(f"catalogue_pages=3 discovered={len(book_urls)} unique_urls={len(unique_urls)}")
