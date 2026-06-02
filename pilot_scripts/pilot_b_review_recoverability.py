"""
Pilot B: Review Recoverability Test
Tests how far back the App Store RSS review feed reaches for each test app.
"""

import urllib.request
import json
import time
from datetime import datetime, timezone

APPS = [
    {"name": "ChatGPT",                    "id": 6448311069, "tier": "Large AI"},
    {"name": "Grammarly",                  "id": 1158877342, "tier": "Medium AI"},
    {"name": "AI Writer: Email Letter",    "id": 1639845219, "tier": "Small AI"},
    {"name": "Spotify",                    "id": 324684580,  "tier": "Large Control"},
    {"name": "Units - Pro Unit Converter", "id": 284574017,  "tier": "Small Control"},
]

POLICY_DATE = datetime(2025, 11, 13, tzinfo=timezone.utc)
COUNTRY = "us"
MAX_PAGES = 10  # RSS feed max: 10 pages × 50 reviews = 500


def fetch_reviews_page(app_id, page, country=COUNTRY):
    url = (
        f"https://itunes.apple.com/rss/customerreviews/"
        f"page={page}/id={app_id}/sortBy=mostRecent/json?cc={country}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        entries = data.get("feed", {}).get("entry", [])
        # First entry on page 1 is app metadata, not a review
        if page == 1 and entries and "im:rating" not in entries[0]:
            entries = entries[1:]
        return entries
    except Exception as e:
        print(f"    [page {page}] error: {e}")
        return []


def parse_date(entry):
    updated = entry.get("updated", {}).get("label", "")
    if not updated:
        return None
    try:
        # Format: 2025-11-14T12:34:56-07:00
        return datetime.fromisoformat(updated).replace(tzinfo=timezone.utc)
    except Exception:
        return None


def test_app(app):
    print(f"\n{'='*60}")
    print(f"  {app['tier']}: {app['name']}  (id={app['id']})")
    print(f"{'='*60}")

    all_dates = []
    total_reviews = 0

    for page in range(1, MAX_PAGES + 1):
        entries = fetch_reviews_page(app["id"], page)
        if not entries:
            print(f"    page {page}: no entries — stopping")
            break

        dates = [parse_date(e) for e in entries]
        dates = [d for d in dates if d]
        total_reviews += len(entries)

        earliest_page = min(dates).strftime("%Y-%m-%d") if dates else "?"
        latest_page   = max(dates).strftime("%Y-%m-%d") if dates else "?"
        print(f"    page {page:2d}: {len(entries):3d} reviews  "
              f"[{earliest_page} … {latest_page}]")

        all_dates.extend(dates)
        time.sleep(0.5)  # polite crawling

    if not all_dates:
        return {**app, "total": 0, "latest": None, "earliest": None,
                "days_covered": None, "velocity": None, "nov2025": False}

    earliest = min(all_dates)
    latest   = max(all_dates)
    days_covered = max((latest - earliest).days, 1)
    velocity = round(total_reviews / days_covered, 1)
    nov2025_reachable = earliest <= POLICY_DATE

    print(f"\n  RESULT:")
    print(f"    Total reviews returned : {total_reviews}")
    print(f"    Latest review          : {latest.strftime('%Y-%m-%d')}")
    print(f"    Earliest review        : {earliest.strftime('%Y-%m-%d')}")
    print(f"    Days covered           : {days_covered}")
    print(f"    Review velocity        : {velocity:.1f} reviews/day")
    print(f"    Nov 2025 reachable     : {'YES ✓' if nov2025_reachable else 'NO ✗'}")

    return {
        **app,
        "total":         total_reviews,
        "latest":        latest.strftime("%Y-%m-%d"),
        "earliest":      earliest.strftime("%Y-%m-%d"),
        "days_covered":  days_covered,
        "velocity":      velocity,
        "nov2025":       nov2025_reachable,
    }


def verdict(results):
    small_apps = [r for r in results if "Small" in r["tier"]]
    reachable_count = sum(1 for r in results if r.get("nov2025"))
    small_reachable = sum(1 for r in small_apps if r.get("nov2025"))

    if small_reachable == len(small_apps):
        return "GREEN", "Small apps reach Nov 2025 — free-tier DiD viable for low-volume apps"
    elif any(r.get("nov2025") for r in results):
        return "YELLOW", "Only some apps reach Nov 2025 — research scope restricted"
    else:
        # Check how far back we actually get
        earliests = [r["earliest"] for r in results if r.get("earliest")]
        if earliests:
            best = min(earliests)
            return "RED", f"No app reaches Nov 2025 (best: {best}) — paid source or redesign required"
        return "RED", "No reviews recovered at all"


def print_summary(results):
    print("\n\n" + "="*75)
    print("PILOT B SUMMARY TABLE")
    print("="*75)
    header = f"{'App':<30} {'Latest':>10} {'Earliest':>10} {'N':>5} {'Days':>5} {'Rev/day':>8} {'Nov2025':>8}"
    print(header)
    print("-"*75)
    for r in results:
        nov = "YES" if r.get("nov2025") else "NO"
        print(
            f"{r['name']:<30} "
            f"{str(r.get('latest','?')):>10} "
            f"{str(r.get('earliest','?')):>10} "
            f"{str(r.get('total','?')):>5} "
            f"{str(r.get('days_covered','?')):>5} "
            f"{str(r.get('velocity','?')):>8} "
            f"{nov:>8}"
        )
    print("="*75)

    color, msg = verdict(results)
    print(f"\nVERDICT: {color}")
    print(f"  {msg}")
    print(f"\nPolicy date: {POLICY_DATE.strftime('%Y-%m-%d')}")
    print(f"Run date:    {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")


if __name__ == "__main__":
    print("Pilot B: Review Recoverability Test")
    print(f"Policy date: {POLICY_DATE.strftime('%Y-%m-%d')}")
    print(f"Testing {len(APPS)} apps, up to {MAX_PAGES} pages each (max {MAX_PAGES*50} reviews)")

    results = []
    for app in APPS:
        result = test_app(app)
        results.append(result)
        time.sleep(1)

    print_summary(results)
