"""yt-bot | requests-based YouTube view bot. Browser ki zaroorat nahi.

Kaise kaam karta hai:
  YouTube player jab video chalti hai to 2 telemetry beacons bhejta hai:
    1. GET /api/stats/playback   -> "viewer ne play kiya" (session init)
    2. GET /api/stats/watchtime  -> st=0 & et>=30 -> VIEW REGISTER hota hai
  Ye script wahi beacons seedhe requests se bhej deta hai.

Env vars:
  VIEWS         is shard me kitne views (default: config.json)
  SHARD         shard number (staggering ke liye)
  USE_PROXIES   1 = proxies.txt se random proxy use karo
"""

import json
import os
import random
import re
import string
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
CBRVER = "131.0.0.0"
CVER = "2.20241120.01.00"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
]

ID_RE = re.compile(r"(?:v=|youtu\.be/|/shorts/|/embed/|/live/|/v/)([A-Za-z0-9_-]{11})")
ALPHABET = string.ascii_letters + string.digits + "-_"


def load_config():
    p = ROOT / "config.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


CFG = load_config()
VIEWS = int(os.environ.get("VIEWS") or CFG.get("views_per_run", 5))
SHARD = int(os.environ.get("SHARD") or 0)
USE_PROXIES = os.environ.get("USE_PROXIES", str(CFG.get("use_proxies", False))).lower() in {"1", "true", "yes"}
TIMEOUT = int(CFG.get("timeout", 20))
STAGGER = CFG.get("stagger_seconds", [0, 240])


def log(msg):
    print("[shard %s] %s" % (SHARD, msg), flush=True)


def extract_id(line):
    line = line.strip()
    m = ID_RE.search(line)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", line):
        return line
    return None


def load_urls():
    p = ROOT / "urls.txt"
    if not p.exists():
        sys.exit("urls.txt nahi mila")
    ids = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        vid = extract_id(line)
        if vid:
            ids.append(vid)
    if not ids:
        sys.exit("urls.txt me koi valid video nahi mila")
    return ids


def load_proxies():
    p = ROOT / "proxies.txt"
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def proxy_dict(raw):
    if not raw:
        return None
    if "://" not in raw:
        raw = "http://" + raw
    return {"http": raw, "https": raw}


def new_cpn():
    return "".join(random.choices(ALPHABET, k=16))


def new_session(proxy_raw=None):
    s = requests.Session()
    s.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    p = proxy_dict(proxy_raw)
    if p:
        s.proxies.update(p)
    return s


def fetch_meta(s, vid):
    """watch page se woh values nikalta hai jo beacon me chahiye."""
    r = s.get(
        "https://www.youtube.com/watch?v=%s&bpctr=9999999999&has_verified=1" % vid,
        timeout=TIMEOUT,
    )
    html = r.text
    m_len = re.search(r'"lengthSeconds":"(\d+)"', html)
    m_cl = re.search(r'"cl":(\d+)', html)
    m_ei = re.search(r'"ei":"([^"]{8,})"', html)
    m_pl = re.search(r'"plid":"([^"]{8,})"', html)

    length = int(m_len.group(1)) if m_len else 0
    if length <= 0:
        length = 60
    return {
        "len": length,
        "cl": m_cl.group(1) if m_cl else str(random.randint(6, 9) * 10 ** 8),
        "ei": m_ei.group(1) if m_ei else "",
        "plid": m_pl.group(1) if m_pl else "",
    }


def base_params(vid, cpn, meta):
    p = {
        "ns": "yt", "el": "detailpage", "cpn": cpn, "ver": "2",
        "fmt": "302", "fs": "0",
        "rt": str(random.randint(150, 1200)), "euri": "",
        "lact": str(random.randint(500, 5000)), "cl": meta["cl"],
        "state": "playing", "volume": "100",
        "cbr": "Chrome", "cbrver": CBRVER, "c": "WEB", "cver": CVER,
        "cplayer": "UNIPLAYER", "cos": "Windows", "cosver": "10.0",
        "cplatform": "DESKTOP", "hl": "en_US", "cr": "US", "uga": "m24",
        "len": str(meta["len"]), "rtn": str(random.randint(30, 300)),
        "afmt": "251", "idpj": "-6", "ldpj": "-30",
        "rti": str(random.randint(1, 60)),
        "docid": vid, "muted": "0", "vis": "0",
    }
    if meta["ei"]:
        p["ei"] = meta["ei"]
    if meta["plid"]:
        p["plid"] = meta["plid"]
    return p


def do_view(vid, proxy_raw=None):
    s = new_session(proxy_raw)
    try:
        meta = fetch_meta(s, vid)
        cpn = new_cpn()

        # 1) playback beacon
        s.get("https://www.youtube.com/api/stats/playback",
              params=base_params(vid, cpn, meta), timeout=TIMEOUT)

        # real player jaisa thoda gap
        time.sleep(random.uniform(1.0, 3.0))

        # 2) watchtime beacon -> yahi view register karta hai
        wt = base_params(vid, cpn, meta)
        et = meta["len"] if meta["len"] <= 30 else 30 + random.randint(0, 3)
        wt["st"] = "0"
        wt["et"] = str(et)
        s.get("https://www.youtube.com/api/stats/watchtime",
              params=wt, timeout=TIMEOUT)
        return meta
    finally:
        s.close()


def main():
    ids = load_urls()
    proxies = load_proxies() if USE_PROXIES else []

    if USE_PROXIES and not proxies:
        log("USE_PROXIES on hai par proxies.txt khaali -> direct IP se")

    if SHARD > 0:
        wait = random.uniform(STAGGER[0], STAGGER[1])
        log("stagger %.0fs" % wait)
        time.sleep(wait)

    log("videos=%d views=%d proxies=%d" % (len(ids), VIEWS, len(proxies)))

    ok = 0
    for i in range(VIEWS):
        vid = ids[i % len(ids)]
        pr = random.choice(proxies) if proxies else None
        try:
            meta = do_view(vid, pr)
            ok += 1
            log("%d/%d ok -> %s (len %ss) [%s]" % (
                i + 1, VIEWS, vid, meta["len"], pr or "direct"))
        except Exception as e:
            log("%d/%d FAIL %s: %s" % (i + 1, VIEWS, vid, e))
        time.sleep(random.uniform(2, 6))

    log("done: %d/%d beacons bheje" % (ok, VIEWS))


if __name__ == "__main__":
    main()
