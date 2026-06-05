#!/usr/bin/env python3
"""
Pilot GP-2: Google Play Historical Version Record Recoverability
================================================================
Goal: For each test app, determine whether complete version history
      (2024-2026) is accessible from free public sources.

Sources tested:
  1. google-play-scraper app() — current version only baseline
  2. APKPure versions page    — community APK archive
  3. APKMirror versions page  — community APK archive
  4. Wayback Machine CDX      — archived Google Play pages

Success criteria:
  GREEN  — >= 10 versions found covering 2024–2026 with dates
  YELLOW — some versions found but incomplete
  RED    — 0 or 1 version (current only)

Test apps:
  ChatGPT   — com.openai.chatgpt
  Grammarly — com.grammarly.android.keyboard
  Spotify   — com.spotify.music
"""

import urllib.request
import json
import re
import time

from google_play_scraper import app as gplay_app

APPS = [
    {"name": "ChatGPT",   "pkg": "com.openai.chatgpt",              "apkpure_slug": "chatgpt",              "apkmirror_slug": "openai/chatgpt"},
    {"name": "Grammarly", "pkg": "com.grammarly.android.keyboard",  "apkpure_slug": "grammarly-keyboard",   "apkmirror_slug": "grammarly/grammarly-keyboard-grammar-checker"},
    {"name": "Spotify",   "pkg": "com.spotify.music",               "apkpure_slug": "spotify-music",        "apkmirror_slug": "spotify-ab/spotify-music-and-podcasts"},
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace"), r.status
    except urllib.error.HTTPError as e:
        return "", e.code
    except Exception as e:
        return "", f"ERR:{e}"


# ── Source 1: google-play-scraper app() ──────────────────────────────────────

def test_gplay_scraper(pkg):
    try:
        info = gplay_app(pkg, lang="en", country="us")
        version = info.get("version", "N/A")
        updated = info.get("updated", "N/A")
        recent  = info.get("recentChangesHTML", "") or ""
        recent_clean = re.sub(r"<[^>]+>", " ", recent).strip()[:120]
        return {
            "status": 200,
            "version": version,
            "updated": str(updated),
            "recent_changes": recent_clean,
            "version_count": 1,
            "note": "current version only",
        }
    except Exception as e:
        return {"status": "ERR", "version_count": 0, "note": str(e)}


# ── Source 2: APKPure ─────────────────────────────────────────────────────────

def test_apkpure(pkg, slug):
    url = f"https://apkpure.com/{slug}/{pkg}/versions"
    html, status = fetch(url)
    if not html:
        return {"status": status, "version_count": 0, "note": f"HTTP {status}"}

    # APKPure version entries: look for version numbers and dates
    # Pattern: version strings like "1.2024.139" and dates like "Jun 5, 2026"
    versions = re.findall(
        r'<span[^>]*class="[^"]*ver-item-n[^"]*"[^>]*>([^<]+)</span>',
        html
    )
    # Also try generic version pattern
    if not versions:
        versions = re.findall(r'>\s*([\d]+\.[\d]+\.[\d.]+)\s*<', html)

    dates = re.findall(
        r'<span[^>]*class="[^"]*date[^"]*"[^>]*>([^<]+)</span>',
        html
    )
    # Fallback date patterns
    if not dates:
        dates = re.findall(
            r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4})',
            html
        )

    count = max(len(versions), len(dates))
    sample = list(zip(versions[:5], dates[:5])) if versions and dates else versions[:5] or dates[:5]

    return {
        "status": status,
        "url": url,
        "page_size": len(html),
        "version_count": count,
        "sample": sample,
        "note": f"{count} version entries detected",
    }


# ── Source 3: APKMirror ───────────────────────────────────────────────────────

def test_apkmirror(slug):
    url = f"https://www.apkmirror.com/apk/{slug}/"
    html, status = fetch(url)
    if not html:
        return {"status": status, "version_count": 0, "note": f"HTTP {status}"}

    # APKMirror version entries: look for release rows
    # Pattern: version listed in app-version widget
    versions = re.findall(
        r'<div[^>]*class="[^"]*apkm-badge[^"]*"[^>]*>([^<]+)</div>',
        html
    )
    # Dates appear in <span class="dateyear_utc"> or similar
    dates = re.findall(
        r'(\d{4}-\d{2}-\d{2})',
        html
    )
    # Also look for release rows
    release_rows = re.findall(
        r'href="[^"]*apk/[^"]*release[^"]*"[^>]*>([^<]+)</a>',
        html
    )

    count = max(len(versions), len(release_rows), len(set(dates[:50])))

    return {
        "status": status,
        "url": url,
        "page_size": len(html),
        "version_count": count,
        "sample_dates": sorted(set(dates), reverse=True)[:5],
        "note": f"{count} version entries detected",
    }


# ── Source 4: Wayback CDX for Google Play page ───────────────────────────────

def test_wayback_cdx(pkg):
    url = (
        f"https://web.archive.org/cdx/search/cdx"
        f"?url=play.google.com/store/apps/details?id={pkg}"
        f"&output=json&from=20240101&to=20261231"
        f"&fl=timestamp,statuscode&filter=statuscode:200&limit=100"
    )
    html, status = fetch(url, timeout=25)
    if not html:
        return {"status": status, "snap_count": 0, "note": f"CDX error: {status}"}
    try:
        rows = json.loads(html)
        snaps = rows[1:] if len(rows) > 1 else []
        dates = sorted(set(r[0][:6] for r in snaps), reverse=True)  # YYYYMM
        return {
            "status": 200,
            "snap_count": len(snaps),
            "months_covered": dates[:12],
            "note": f"{len(snaps)} HTTP-200 snapshots (2024–2026)",
        }
    except Exception as e:
        return {"status": "parse_err", "snap_count": 0, "note": str(e)}


# ── Verdict ───────────────────────────────────────────────────────────────────

def verdict(best_count):
    if best_count >= 10:
        return "GREEN  — >= 10 versions found, history appears complete"
    if best_count >= 3:
        return "YELLOW — some versions found, history is partial"
    return "RED    — 0–2 versions (current only or unavailable)"


# ── Main ──────────────────────────────────────────────────────────────────────

def run_app(app):
    name = app["name"]
    pkg  = app["pkg"]
    print(f"\n{'='*62}")
    print(f"  {name}  ({pkg})")
    print(f"{'='*62}")

    results = {}

    # 1. google-play-scraper
    print(f"\n── Source 1: google-play-scraper app() ──")
    r1 = test_gplay_scraper(pkg)
    results["gplay_scraper"] = r1
    print(f"   Version : {r1.get('version','N/A')}")
    print(f"   Updated : {r1.get('updated','N/A')}")
    print(f"   Changes : {r1.get('recent_changes','')[:80]}")
    print(f"   Count   : {r1['version_count']}  ({r1.get('note','')})")
    time.sleep(1)

    # 2. APKPure
    print(f"\n── Source 2: APKPure versions page ──")
    r2 = test_apkpure(pkg, app["apkpure_slug"])
    results["apkpure"] = r2
    print(f"   HTTP    : {r2['status']}   Size: {r2.get('page_size',0):,} bytes")
    print(f"   Count   : {r2['version_count']}  ({r2.get('note','')})")
    if r2.get("sample"):
        print(f"   Sample  : {r2['sample'][:3]}")
    time.sleep(2)

    # 3. APKMirror
    print(f"\n── Source 3: APKMirror versions page ──")
    r3 = test_apkmirror(app["apkmirror_slug"])
    results["apkmirror"] = r3
    print(f"   HTTP    : {r3['status']}   Size: {r3.get('page_size',0):,} bytes")
    print(f"   Count   : {r3['version_count']}  ({r3.get('note','')})")
    if r3.get("sample_dates"):
        print(f"   Dates   : {r3['sample_dates']}")
    time.sleep(2)

    # 4. Wayback CDX
    print(f"\n── Source 4: Wayback CDX (Google Play page, 2024–2026) ──")
    r4 = test_wayback_cdx(pkg)
    results["wayback_cdx"] = r4
    print(f"   Snapshots: {r4['snap_count']}  ({r4.get('note','')})")
    if r4.get("months_covered"):
        print(f"   Months  : {r4['months_covered'][:8]}")
    time.sleep(2)

    best = max(
        r1["version_count"],
        r2["version_count"],
        r3["version_count"],
    )
    v = verdict(best)
    print(f"\n  VERDICT: {v}")
    print(f"  Best source count: {best}")

    return {"name": name, "pkg": pkg, "results": results, "best_count": best, "verdict": v}


def main():
    print("=" * 62)
    print("  Pilot GP-2: Google Play Version History Recoverability")
    print("  Apps: ChatGPT, Grammarly, Spotify")
    print("  Sources: google-play-scraper / APKPure / APKMirror / Wayback")
    print("=" * 62)

    all_results = []
    for app in APPS:
        r = run_app(app)
        all_results.append(r)
        time.sleep(2)

    print(f"\n{'='*62}")
    print("  SUMMARY")
    print(f"{'='*62}")
    print(f"\n  {'App':<12} {'Best count':>10}  Verdict")
    print(f"  {'-'*58}")
    for r in all_results:
        print(f"  {r['name']:<12} {r['best_count']:>10}  {r['verdict']}")

    # Per-source breakdown
    print(f"\n  Per-source version counts:")
    print(f"  {'App':<12} {'gplay':>6} {'APKPure':>8} {'APKMirror':>10} {'Wayback snaps':>14}")
    print(f"  {'-'*54}")
    for r in all_results:
        rs = r["results"]
        print(
            f"  {r['name']:<12}"
            f" {rs['gplay_scraper']['version_count']:>6}"
            f" {rs['apkpure']['version_count']:>8}"
            f" {rs['apkmirror']['version_count']:>10}"
            f" {rs['wayback_cdx']['snap_count']:>14}"
        )


if __name__ == "__main__":
    main()
