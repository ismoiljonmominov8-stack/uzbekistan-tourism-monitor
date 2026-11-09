"""One-off: find free-licensed photos for the campaign pages on Wikimedia Commons and download them with their
author and licence (run on GitHub: this workspace cannot reach wikimedia.org).

For each topic: search the File namespace (first among Commons "Quality images", then all files), keep large JPEGs
under CC0 / public domain / CC BY / CC BY-SA, and save a 1600 px copy plus the metadata needed for the credit line.
Output: landing/photos/raw/<topic>_<k>.jpg and landing/photos/raw/meta.json
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "uzbekistan-tourism-monitor/1.0 (https://github.com/ismoiljonmominov8-stack/uzbekistan-tourism-monitor)"}
OUT = Path(__file__).resolve().parents[1] / "landing" / "photos" / "raw"
TOPICS = {
    "registan": "Registan Samarkand",
    "shahizinda": "Shah-i-Zinda Samarkand",
    "gur": "Gur-e-Amir Samarkand",
    "khiva": "Itchan Kala Khiva",
    "bukhara": "Kalyan minaret Bukhara",
    "plov": "plov Uzbekistan",
    "train": "Afrosiyob train",
    "chorsu": "Chorsu bazaar Tashkent",
    "metro": "Tashkent metro station",
}
PER_TOPIC = 6
FREE = re.compile(r"^(cc0|public domain|pd|cc by(-sa)? \d(\.\d)?)", re.I)


def clean(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()


def search(query: str, quality: bool) -> list[dict]:
    q = f'{query} incategory:"Quality_images"' if quality else query
    r = requests.get(API, headers=UA, timeout=60, params={
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrlimit": 40,
        "gsrsearch": f"{q} filetype:bitmap", "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": 1600})
    r.raise_for_status()
    pages = (r.json().get("query") or {}).get("pages", {})
    out = []
    for p in sorted(pages.values(), key=lambda p: p.get("index", 999)):
        ii = (p.get("imageinfo") or [{}])[0]
        md = ii.get("extmetadata", {})
        lic = clean(md.get("LicenseShortName", {}).get("value", ""))
        if ii.get("mime") != "image/jpeg" or ii.get("width", 0) < 1800 or not FREE.match(lic):
            continue
        out.append({"title": p["title"], "thumb": ii.get("thumburl"), "page": ii.get("descriptionurl"),
                    "width": ii.get("width"), "height": ii.get("height"), "license": lic,
                    "license_url": clean(md.get("LicenseUrl", {}).get("value", "")),
                    "author": clean(md.get("Artist", {}).get("value", ""))[:120] or "unknown",
                    "quality": quality})
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {}
    for key, query in TOPICS.items():
        found, seen = [], set()
        for quality in (True, False):
            try:
                for x in search(query, quality):
                    if x["title"] not in seen:
                        seen.add(x["title"]); found.append(x)
            except Exception as e:  # noqa: BLE001
                print("search failed", key, quality, e)
            time.sleep(1)
        for k, x in enumerate(found[:PER_TOPIC]):
            name = f"{key}_{k}.jpg"
            try:
                img = requests.get(x["thumb"], headers=UA, timeout=120)
                img.raise_for_status()
                (OUT / name).write_bytes(img.content)
                meta[name] = x
                print("saved", name, x["title"], x["license"], x["author"][:40])
            except Exception as e:  # noqa: BLE001
                print("download failed", name, e)
            time.sleep(1)
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(meta), "photos")


if __name__ == "__main__":
    main()
