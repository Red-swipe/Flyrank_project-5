from pathlib import Path

import requests


BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_FILE = BASE_DIR / "cache" / "catalogue-page-1.html"
URL = "https://books.toscrape.com/"
HEADERS = {
    "User-Agent": "FlyRankInternshipA9/1.0 ([https://github.com/Red-swipe/Flyrank_project-5](https://github.com/Red-swipe/Flyrank_project-5))"
}


if CACHE_FILE.exists():
    content = CACHE_FILE.read_bytes()
    print("CACHE HIT")
else:
    response = requests.get(URL, headers=HEADERS, timeout=10)
    if response.status_code != 200:
        print(f"ERROR: received status code {response.status_code}")
        raise SystemExit(1)

    content = response.content
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_bytes(content)
    print("FETCH")

print(f"Response size: {len(content)} bytes")
