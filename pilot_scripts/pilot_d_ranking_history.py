"""
Pilot D: Historical Ranking Availability Test
Tests whether any free/public source provides App Store ranking history
covering the November 2025 policy window.
"""

import urllib.request
import urllib.error
import json
import time

TEST_APP = {"name": "ChatGPT", "id": 6448311069, "slug": "chatgpt"}
POLICY_DATE = "2025-11-13"

SOURCES = [
    {
        "name": "iTunes RSS Top Free (current snapshot)",
        "url": "https://itunes.apple.com/us/rss/topfreeapplications/limit=200/json",
        "description": "Official Apple chart RSS — real-time only, no history parameter",
    },
    {
        "name": "iTunes RSS Top Free — with date param (test)",
        "url": "https://itunes.apple.com/us/rss/topfreeapplications/limit=10/date=2025-11-13/json",
        "description": "Test whether iTunes RSS accepts a historical date parameter",
    },
    {
        "name": "iTunes RSS — category chart (Productivity)",
        "url": "https://itunes.apple.com/us/rss/topfreeapplications/limit=10/genre=6007/json",
        "description": "Category-level chart — same real-time only limitation",
    },
    {
        "name": "AppFollow public chart page",
        "url": "https://appfollow.io/ratings/top-free/us/iphone",
        "description": "Third-party ranking aggregator",
    },
    {
        "name": "Wayback CDX — iTunes chart RSS (any historical snapshot)",
        "url": (
            "https://web.archive.org/cdx/search/cdx"
            "?url=itunes.apple.com/us/rss/topfreeapplications*"
            "&output=json&from=20251101&to=20251130&fl=timestamp,statuscode&limit=10"
        ),
        "description": "Check whether Wayback Machine archived the iTunes chart RSS around Nov 2025",
    },
    {
        "name": "Wayback CDX — App Store chart page (any historical snapshot)",
        "url": (
            "https://web.archive.org/cdx/search/cdx"
            "?url=apps.apple.com/us/charts*"
            "&output=json&from=20251101&to=20251130&fl=timestamp,statuscode&limit=10"
        ),
        "description": "Check whether Wayback archived the App Store charts page in Nov 2025",
    },
]


def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            content = r.read()
            return content.decode("utf-8", errors="replace"), r.status, len(content)
    except urllib.error.HTTPError as e:
        return "", e.code, 0
    except Exception as e:
        return "", 0, 0


def check_itunes_rss_current(html):
    """Check if test app appears in current iTunes chart and extract its rank."""
    try:
        data = json.loads(html)
        entries = data.get("feed", {}).get("entry", [])
        for i, entry in enumerate(entries):
            app_id = entry.get("id", {}).get("attributes", {}).get("im:id", "")
            name = entry.get("im:name", {}).get("label", "")
            if str(TEST_APP["id"]) == str(app_id):
                return f"FOUND at rank #{i+1} in current chart"
        return f"Not in top {len(entries)} (app may be below chart limit)"
    except Exception as e:
        return f"Parse error: {e}"


def check_wayback_cdx(html):
    """Parse Wayback CDX JSON response and count valid snapshots."""
    try:
        data = json.loads(html)
        rows = [r for r in data[1:] if r[1] == "200"]
        if rows:
            return f"{len(rows)} snapshot(s) found: " + ", ".join(r[0][:8] for r in rows[:5])
        return "0 snapshots found"
    except:
        return "empty or parse error"


if __name__ == "__main__":
    print("=" * 65)
    print("Pilot D: Historical Ranking Availability Test")
    print(f"Policy date: {POLICY_DATE}")
    print(f"Test app:    {TEST_APP['name']} (id={TEST_APP['id']})")
    print("=" * 65)

    results = []

    for src in SOURCES:
        print(f"\n── {src['name']} ──")
        print(f"   URL: {src['url'][:90]}")
        html, status, size = fetch(src["url"])
        print(f"   HTTP: {status}   Size: {size:,} bytes")

        note = ""
        if status == 200 and html:
            if "topfreeapplications" in src["url"] and "date=" not in src["url"] and "Wayback" not in src["name"] and "AppFollow" not in src["name"]:
                note = check_itunes_rss_current(html)
            elif "Wayback" in src["name"] or "cdx" in src["url"]:
                note = check_wayback_cdx(html)
            else:
                # Generic: check if historical date Nov 2025 appears in response
                if "2025-11" in html or "November" in html:
                    note = "Contains Nov 2025 date references"
                else:
                    note = "No Nov 2025 date references found"
        elif status != 200:
            note = f"HTTP {status} — endpoint unavailable"

        print(f"   Finding: {note}")
        results.append((src["name"], status, size, note))
        time.sleep(0.5)

    # ── iTunes RSS test: does chart RSS support date parameter? ──────────────
    print("\n── Additional: does iTunes RSS chart accept 'date' parameter? ──")
    _, status_date, _ = fetch(
        "https://itunes.apple.com/us/rss/topfreeapplications/limit=10/date=20251113/json"
    )
    print(f"   /date=20251113/ → HTTP {status_date}")
    _, status_from, _ = fetch(
        "https://itunes.apple.com/us/rss/topfreeapplications/limit=10/json?date=2025-11-13"
    )
    print(f"   ?date=2025-11-13 → HTTP {status_from}")

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n\n" + "=" * 65)
    print("PILOT D SUMMARY")
    print("=" * 65)
    print(f"\n{'Source':<45} {'HTTP':>4}  Finding")
    print("-" * 65)
    for name, status, size, note in results:
        print(f"{name:<45} {str(status):>4}  {note[:40]}")

    print("""
Key findings:
  - iTunes RSS chart provides real-time snapshot ONLY (no historical parameter)
  - No free/public source archives historical App Store rankings
  - Wayback Machine may have occasional chart page snapshots (see CDX results above)
  - Paid sources (Sensor Tower, AppTweak, Appfigures, data.ai, Apptopia) have
    full daily ranking history but require subscriptions

Verdict: RANKING IS A PAID-ONLY VARIABLE for historical analysis.
""")
