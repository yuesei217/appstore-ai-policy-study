"""
Pilot A: Privacy Label Feasibility Test
A1: Can current Privacy Nutrition Labels be retrieved programmatically?
A2: Can historical privacy labels (pre-Nov 2025) be recovered via Wayback Machine?
"""

import urllib.request
import json
import re
import time
from datetime import datetime, timezone

TEST_APP = {"name": "ChatGPT", "id": 6448311069, "slug": "chatgpt"}
POLICY_DATE = "2025-11-13"

# ── A1 helpers ────────────────────────────────────────────────────────────────

def test_itunes_api(app_id):
    """Check whether iTunes Lookup API returns any privacy-related fields."""
    url = f"https://itunes.apple.com/lookup?id={app_id}&country=us"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    fields = sorted(data["results"][0].keys())
    privacy_fields = [f for f in fields if any(x in f.lower() for x in ["privacy", "data", "track", "linked", "consent", "ai"])]
    print(f"  All fields ({len(fields)}): {fields}")
    print(f"  Privacy-adjacent fields: {privacy_fields}")
    return privacy_fields


def fetch_html(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="replace")


def extract_privacy_section(html):
    """Extract all privacy label sections from App Store page HTML."""
    sections = {}
    labels = [
        "Data Used to Track You",
        "Data Linked to You",
        "Data Not Linked to You",
        "Data Not Collected",
    ]
    for label in labels:
        idx = html.find(label)
        if idx < 0:
            continue
        chunk = html[idx: idx + 4000]
        text = re.sub(r"<[^>]+>", " ", chunk)
        text = re.sub(r"\s+", " ", text).strip()
        # Trim at next section
        for other in labels:
            if other != label:
                end = text.find(other)
                if 0 < end < len(text):
                    text = text[:end]
                    break
        sections[label] = text[:800]
    return sections


def test_html_scraping(app_id, app_slug):
    """Scrape current App Store page for privacy labels."""
    url = f"https://apps.apple.com/us/app/{app_slug}/id{app_id}"
    html = fetch_html(url)
    print(f"  Page size: {len(html):,} bytes")

    for phrase in ["Data Linked to You", "Data Not Linked to You", "Data Used to Track", "privacyTypes"]:
        print(f"  \"{phrase}\": {html.count(phrase)} occurrence(s)")

    sections = extract_privacy_section(html)
    print(f"  Sections found: {list(sections.keys())}")
    for k, v in sections.items():
        print(f"\n  [{k}]")
        # Extract just the meaningful text (skip SVG content)
        clean = re.sub(r'<path[^>]*>.*?</path>', ' ', v, flags=re.DOTALL)
        print(f"  {clean[:400]}")
    return sections


# ── A2 helpers ────────────────────────────────────────────────────────────────

def get_wayback_snapshots(app_id, from_ts, to_ts, limit=200):
    """Query Wayback Machine CDX API for snapshot list."""
    url = (
        f"https://web.archive.org/cdx/search/cdx"
        f"?url=apps.apple.com/us/app/*/{app_id}"
        f"&output=json&from={from_ts}&to={to_ts}"
        f"&fl=timestamp,statuscode&limit={limit}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read())
    return [row for row in data[1:] if row[1] == "200"]


def fetch_wayback_snapshot(timestamp, url):
    """Fetch a specific Wayback Machine snapshot."""
    wb_url = f"https://web.archive.org/web/{timestamp}/{url}"
    req = urllib.request.Request(wb_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", errors="replace")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = TEST_APP
    print("=" * 65)
    print(f"Pilot A: Privacy Label Feasibility — {app['name']} (id={app['id']})")
    print(f"Policy date: {POLICY_DATE}")
    print("=" * 65)

    # ── A1a: iTunes API ──────────────────────────────────────────────────────
    print("\n── A1a: iTunes Lookup API ──")
    privacy_fields = test_itunes_api(app["id"])
    print(f"  Result: {'FOUND' if privacy_fields else 'NOT FOUND — no privacy fields in iTunes API'}")

    # ── A1b: HTML scraping ───────────────────────────────────────────────────
    print("\n── A1b: App Store HTML scraping (current state) ──")
    sections = test_html_scraping(app["id"], app["slug"])
    print(f"\n  Result: {'FOUND — ' + str(len(sections)) + ' privacy sections extracted' if sections else 'NOT FOUND'}")

    time.sleep(1)

    # ── A2: Wayback Machine ──────────────────────────────────────────────────
    print("\n── A2: Wayback Machine historical coverage ──")

    apps_to_check = [
        {"name": "ChatGPT",   "id": 6448311069},
        {"name": "Grammarly", "id": 1158877342},
        {"name": "AI Writer", "id": 1639845219},
    ]

    print(f"\n  Snapshot counts in policy window (Oct 1 – Dec 31, 2025):")
    coverage = {}
    for a in apps_to_check:
        try:
            snaps = get_wayback_snapshots(a["id"], "20251001", "20260101")
            coverage[a["name"]] = snaps
            print(f"  {a['name']:<20}: {len(snaps):>4} snapshots")
        except Exception as e:
            print(f"  {a['name']:<20}: error — {e}")
        time.sleep(0.5)

    # ── A2: Content comparison for ChatGPT ──────────────────────────────────
    print("\n── A2: Pre/Post policy privacy label comparison (ChatGPT) ──")

    snapshots_to_compare = [
        ("Pre-policy  (Oct 24, 2025)", "20251024135100"),
        ("Policy day  (Nov 13, 2025)", "20251113161400"),
        ("Post-policy (Nov 25, 2025)", "20251125050300"),
    ]

    app_url = f"https://apps.apple.com/us/app/{app['slug']}/id{app['id']}"
    for label, ts in snapshots_to_compare:
        print(f"\n  === {label} ===")
        try:
            html = fetch_wayback_snapshot(ts, app_url)
            secs = extract_privacy_section(html)
            if secs:
                for k, v in secs.items():
                    clean = re.sub(r'<path[^>]*>', ' ', v)
                    clean = re.sub(r'\s+', ' ', clean).strip()
                    print(f"  [{k}]")
                    print(f"  {clean[:400]}")
            else:
                print("  No privacy sections found in this snapshot.")
        except Exception as e:
            print(f"  Error: {e}")
        time.sleep(1.5)

    print("\n── Summary ──")
    print("  A1 (current labels via HTML):   VIABLE")
    print("  A1 (current labels via iTunes): NOT AVAILABLE")
    print(f"  A2 (historical via Wayback):    CONDITIONAL ({len(coverage.get('ChatGPT',[]))} snaps for ChatGPT; 0 for Grammarly)")
