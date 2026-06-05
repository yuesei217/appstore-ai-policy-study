#!/usr/bin/env python3
"""
Pilot GP-1: Google Play Historical Review Recoverability
=========================================================
Goal: For each test app, paginate through reviews sorted by newest and
      determine the earliest review date reachable.

Success criteria:
  GREEN  — earliest date <= 2021-01-01  (full 2021–2025 coverage)
  YELLOW — earliest date between 2021 and 2024-01-01
  RED    — earliest date >= 2024-01-01  (cannot reach policy window)

Test apps:
  ChatGPT  — com.openai.chatgpt      (large AI app)
  Grammarly — com.grammarly.android.keyboard  (medium AI app)
  Spotify  — com.spotify.music       (large control app)
"""

from google_play_scraper import reviews, Sort
from datetime import datetime, timezone
import time

APPS = [
    {"name": "ChatGPT",   "pkg": "com.openai.chatgpt"},
    {"name": "Grammarly", "pkg": "com.grammarly.android.keyboard"},
    {"name": "Spotify",   "pkg": "com.spotify.music"},
]

TARGET_DATE   = datetime(2021, 1, 1, tzinfo=timezone.utc)
POLICY_DATE   = datetime(2025, 11, 13, tzinfo=timezone.utc)
BATCH_SIZE    = 200   # reviews per API call
MAX_BATCHES   = 50    # hard cap: 50 × 200 = 10,000 reviews max per app
DELAY_SECS    = 2     # between batches


def verdict(earliest_dt):
    if earliest_dt is None:
        return "RED   — 0 reviews returned"
    if earliest_dt <= TARGET_DATE:
        return "GREEN — reaches 2021 or earlier"
    if earliest_dt <= datetime(2024, 1, 1, tzinfo=timezone.utc):
        return f"YELLOW — reaches {earliest_dt.strftime('%Y-%m')}, before 2024"
    if earliest_dt <= POLICY_DATE:
        return f"YELLOW — reaches {earliest_dt.strftime('%Y-%m')}, before policy date"
    return f"RED   — earliest: {earliest_dt.strftime('%Y-%m-%d')} (after policy date)"


def run_app(name, pkg):
    print(f"\n{'='*60}")
    print(f"  {name}  ({pkg})")
    print(f"{'='*60}")

    total      = 0
    earliest   = None
    latest     = None
    token      = None
    reached_target = False

    for batch_num in range(1, MAX_BATCHES + 1):
        try:
            result, token = reviews(
                pkg,
                lang="en",
                country="us",
                sort=Sort.NEWEST,
                count=BATCH_SIZE,
                continuation_token=token,
            )
        except Exception as e:
            print(f"  [batch {batch_num}] ERROR: {e}")
            break

        if not result:
            print(f"  [batch {batch_num}] Empty response — no more reviews")
            break

        batch_dates = [r["at"] for r in result if r.get("at")]
        if not batch_dates:
            print(f"  [batch {batch_num}] No timestamps in batch")
            break

        batch_min = min(batch_dates)
        batch_max = max(batch_dates)

        # ensure timezone-aware for comparison
        if batch_min.tzinfo is None:
            batch_min = batch_min.replace(tzinfo=timezone.utc)
        if batch_max.tzinfo is None:
            batch_max = batch_max.replace(tzinfo=timezone.utc)

        total += len(result)
        if earliest is None or batch_min < earliest:
            earliest = batch_min
        if latest is None or batch_max > latest:
            latest = batch_max

        print(f"  [batch {batch_num:>2}]  {len(result):>3} reviews  "
              f"batch range: {batch_min.strftime('%Y-%m-%d')} – {batch_max.strftime('%Y-%m-%d')}  "
              f"total so far: {total:,}")

        if batch_min <= TARGET_DATE:
            print(f"  → Reached target date ({TARGET_DATE.strftime('%Y-%m-%d')}) — stopping")
            reached_target = True
            break

        if token is None:
            print(f"  → No continuation token — end of available reviews")
            break

        time.sleep(DELAY_SECS)

    print()
    print(f"  Total reviews fetched : {total:,}")
    print(f"  Latest review date    : {latest.strftime('%Y-%m-%d') if latest else 'N/A'}")
    print(f"  Earliest review date  : {earliest.strftime('%Y-%m-%d') if earliest else 'N/A'}")
    print(f"  Reached 2021 target   : {'YES' if reached_target else 'NO'}")
    print(f"  Nov 2025 reachable    : {'YES' if earliest and earliest <= POLICY_DATE else 'NO'}")
    v = verdict(earliest)
    print(f"  VERDICT               : {v}")

    return {
        "name": name, "pkg": pkg,
        "total": total, "earliest": earliest, "latest": latest,
        "reached_target": reached_target, "verdict": v,
    }


def main():
    print("=" * 60)
    print("  Pilot GP-1: Google Play Review Recoverability")
    print(f"  Target: earliest date <= {TARGET_DATE.strftime('%Y-%m-%d')}")
    print(f"  Policy date: {POLICY_DATE.strftime('%Y-%m-%d')}")
    print(f"  Max per app: {MAX_BATCHES} batches × {BATCH_SIZE} = {MAX_BATCHES*BATCH_SIZE:,} reviews")
    print("=" * 60)

    results = []
    for app in APPS:
        r = run_app(app["name"], app["pkg"])
        results.append(r)
        time.sleep(3)

    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    print(f"  {'App':<12} {'Total':>8}  {'Earliest':<12}  {'Nov2025?':>8}  Verdict")
    print(f"  {'-'*56}")
    for r in results:
        earliest_str = r["earliest"].strftime("%Y-%m-%d") if r["earliest"] else "N/A"
        nov = "YES" if r["earliest"] and r["earliest"] <= POLICY_DATE else "NO"
        print(f"  {r['name']:<12} {r['total']:>8,}  {earliest_str:<12}  {nov:>8}  {r['verdict']}")


if __name__ == "__main__":
    main()
