"""Free proxy list fetch karke test karta hai, sirf chalne wale proxies.txt me likhta hai.

    python refresh_proxies.py

Note: free proxies ka hit-rate ~10-20% hota hai. Sab chalenge aisa mat sochna.
"""

import concurrent.futures as cf
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "proxies.txt"

SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
]

TEST_URL = "https://www.youtube.com/generate_204"
KEEP = 60
WORKERS = 100
TIMEOUT = 6


def fetch(url):
    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            return [l.strip() for l in r.text.splitlines() if l.strip()]
    except Exception as e:
        print("  source fail: %s (%s)" % (url.split("/")[4], e))
    return []


def alive(proxy):
    p = proxy if "://" in proxy else "http://" + proxy
    try:
        r = requests.get(TEST_URL, proxies={"http": p, "https": p}, timeout=TIMEOUT)
        if r.status_code in (200, 204):
            return proxy
    except Exception:
        pass
    return None


def main():
    pool = set()
    for url in SOURCES:
        got = fetch(url)
        print("  %s -> %d" % (url.split("/")[4], len(got)))
        pool.update(got)

    pool = sorted(pool)
    print("total unique: %d" % len(pool))
    if not pool:
        print("koi proxy nahi mila, internet check kar")
        sys.exit(1)

    print("testing %d proxies (%d workers)..." % (len(pool), WORKERS))
    good = []
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for res in ex.map(alive, pool):
            if res:
                good.append(res)
                print("  live: %s" % res)
                if len(good) >= KEEP:
                    break

    if not good:
        print("ek bhi live proxy nahi mila. thodi der baad try kar.")
        sys.exit(1)

    lines = ["# auto-generated, %d live proxies" % len(good)] + good
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("likh diya: proxies.txt (%d proxies)" % len(good))


if __name__ == "__main__":
    main()
