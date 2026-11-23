"""
Step 1: download the Queensland Health public dental waiting list files.

Source: Queensland Government open data portal (data.qld.gov.au).
Covers July 2021 to the latest release. Files are saved to data/raw/.
"""
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://www.data.qld.gov.au/api/3/action/package_search"
YEARS = re.compile(r"(20\d\d)-20\d\d$")
RAW = Path("data/raw")
HEADERS = {"User-Agent": "nl-to-sql-evaluation (portfolio project)"}


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def main():
    RAW.mkdir(parents=True, exist_ok=True)

    query = urllib.parse.urlencode({"q": 'title:"public dental waiting"', "rows": 50})
    results = json.loads(get(f"{API}?{query}"))["result"]["results"]
    datasets = [d for d in results
                if (m := YEARS.search(d["name"])) and int(m.group(1)) >= 2021]
    print(f"Datasets found: {len(datasets)}")

    count = 0
    for dataset in sorted(datasets, key=lambda d: d["name"]):
        for resource in dataset["resources"]:
            url = resource["url"]
            name = url.split("/")[-1]
            if not name.lower().endswith((".xls", ".xlsx")):
                print(f"  skipped (not Excel): {resource['name']}")
                continue
            target = RAW / name
            if target.exists():
                print(f"  already downloaded: {name}")
            else:
                target.write_bytes(get(url))
                print(f"  downloaded: {name}")
                time.sleep(1)
            count += 1

    print(f"Excel files in data/raw: {count}")


if __name__ == "__main__":
    main()