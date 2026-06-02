#!/usr/bin/env python3
"""
Stage 1: Coverage Census  (v2 — polite rate limiting)
======================================================
For each target app, query Wayback CDX and count usable snapshots in the
Oct 1 – Dec 31, 2025 policy window. No page fetching; no HTML parsing.

Rate limit strategy:
  - 15 seconds between CDX requests (was 3 — caused blanket rate limiting)
  - Exponential backoff: on timeout, sleep 30s then 60s before giving up
  - Availability API warm-up: before each CDX query, check Wayback Availability
    API (separate endpoint, separate rate limit) to confirm at least one
    snapshot exists — skip CDX entirely if availability returns nothing
  - Incremental CSV save: survives interruption; re-run skips completed rows

Go/No-Go gate:
  AI apps   with >= MIN_SNAPS snapshots in window  >= MIN_AI_APPS
  Non-AI apps with >= MIN_SNAPS snapshots in window >= MIN_CTRL_APPS

Stage 2 variables (to extract for apps passing the gate):
  1. "Data Used to Track You"     — present / absent (primary treatment indicator)
  2. "Data Linked to You"         — full section text (captures category list changes)
  3. "Data Not Linked to You"     — present / absent
  4. "Third-Party Advertising"    — mention count (ad-tracking disclosure proxy)
  5. "artificial intelligence"/AI mentions in privacy section text
  Store all five even if primary analysis uses only (1), to hedge against
  reviewer pushback on treatment definition.
"""

import urllib.request
import urllib.parse
import json
import time
import csv
import os

# ── Gate thresholds ────────────────────────────────────────────────────────────
MIN_SNAPS     = 3    # minimum usable snapshots in Oct–Dec 2025 window
MIN_AI_APPS   = 10
MIN_CTRL_APPS = 10

# ── Policy window ──────────────────────────────────────────────────────────────
WINDOW_FROM = "20251001"
WINDOW_TO   = "20251231"

# ── Rate limiting ──────────────────────────────────────────────────────────────
DELAY_BETWEEN  = 15   # seconds between CDX requests
RETRY_DELAYS   = [30, 60]  # backoff waits on timeout before giving up
CDX_TIMEOUT    = 30
AVAIL_TIMEOUT  = 10

# ── Target app list ────────────────────────────────────────────────────────────
APPS = [
    # ── AI apps (treatment group candidates) ──────────────────────────────────
    {"name": "ChatGPT",              "id": "6448311069",  "is_ai": True},
    {"name": "Claude (Anthropic)",   "id": "1640358807",  "is_ai": True},
    {"name": "Perplexity AI",        "id": "1673966783",  "is_ai": True},
    {"name": "Microsoft Copilot",    "id": "741299935",   "is_ai": True},
    {"name": "Grok",                 "id": "6670324846",  "is_ai": True},
    {"name": "Google Gemini",        "id": "6477489729",  "is_ai": True},
    {"name": "Grammarly",            "id": "1158877342",  "is_ai": True},
    {"name": "Character.AI",         "id": "1660271479",  "is_ai": True},
    {"name": "Poe",                  "id": "1640230998",  "is_ai": True},
    {"name": "Replika",              "id": "1271467338",  "is_ai": True},
    {"name": "Pi AI",                "id": "6446749052",  "is_ai": True},
    {"name": "DeepSeek",             "id": "6738070139",  "is_ai": True},
    {"name": "Sora by OpenAI",       "id": "6744034028",  "is_ai": True},
    {"name": "Otter.ai",             "id": "1237743424",  "is_ai": True},
    {"name": "Jasper AI",            "id": "1606449088",  "is_ai": True},
    {"name": "Adobe Firefly",        "id": "1609473439",  "is_ai": True},
    {"name": "Runway",               "id": "1665024375",  "is_ai": True},
    {"name": "Speechify",            "id": "1209815023",  "is_ai": True},
    {"name": "Nova - AI Chatbot",    "id": "1669807299",  "is_ai": True},
    {"name": "AI Writer Pro",        "id": "1639845219",  "is_ai": True},

    # ── Non-AI control apps ───────────────────────────────────────────────────
    {"name": "Spotify",              "id": "324684580",   "is_ai": False},
    {"name": "Netflix",              "id": "363590051",   "is_ai": False},
    {"name": "YouTube",              "id": "544007664",   "is_ai": False},
    {"name": "Instagram",            "id": "389801252",   "is_ai": False},
    {"name": "TikTok",               "id": "835599320",   "is_ai": False},
    {"name": "Twitter / X",          "id": "333903271",   "is_ai": False},
    {"name": "Facebook",             "id": "284882215",   "is_ai": False},
    {"name": "Gmail",                "id": "422689480",   "is_ai": False},
    {"name": "WhatsApp",             "id": "310633997",   "is_ai": False},
    {"name": "Slack",                "id": "618783545",   "is_ai": False},
    {"name": "Zoom",                 "id": "546505307",   "is_ai": False},
    {"name": "Uber",                 "id": "368677368",   "is_ai": False},
    {"name": "DoorDash",             "id": "719972451",   "is_ai": False},
    {"name": "Amazon Shopping",      "id": "297606951",   "is_ai": False},
    {"name": "Airbnb",               "id": "401626263",   "is_ai": False},
    {"name": "Dropbox",              "id": "327630330",   "is_ai": False},
    {"name": "LinkedIn",             "id": "288429040",   "is_ai": False},
    {"name": "ESPN",                 "id": "317469184",   "is_ai": False},
    {"name": "Pandora",              "id": "284035177",   "is_ai": False},
    {"name": "Evernote",             "id": "281796108",   "is_ai": False},
]

OUTPUT_FILE = "stage1_results.csv"


# ── HTTP helpers ───────────────────────────────────────────────────────────────

def fetch_json(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def check_availability(app_id, timestamp="20251101"):
    """
    Wayback Availability API — separate endpoint from CDX, lighter rate limit.
    Returns True if at least one snapshot exists near the given timestamp.
    """
    url = (
        f"https://archive.org/wayback/available"
        f"?url=apps.apple.com/us/app/id{app_id}"
        f"&timestamp={timestamp}"
    )
    try:
        data = fetch_json(url, AVAIL_TIMEOUT)
        snap = data.get("archived_snapshots", {}).get("closest", {})
        return snap.get("available", False), snap.get("timestamp", "")
    except Exception as e:
        return False, f"avail_err:{e}"


def fetch_cdx_with_backoff(app_id):
    """
    Query CDX for snapshot count in the policy window.
    Returns (total_usable, total_200, timestamps_list, error_str).
    Retries with exponential backoff on timeout.
    """
    url = (
        f"https://web.archive.org/cdx/search/cdx"
        f"?url=apps.apple.com/us/app/*/id{app_id}"
        f"&output=json&from={WINDOW_FROM}&to={WINDOW_TO}"
        f"&fl=timestamp,statuscode&limit=500"
    )
    delays = [0] + RETRY_DELAYS
    last_err = ""
    for wait in delays:
        if wait:
            print(f"      (retry after {wait}s...)", end="", flush=True)
            time.sleep(wait)
        try:
            data = fetch_json(url, CDX_TIMEOUT)
            if len(data) <= 1:
                return 0, 0, [], ""
            rows = data[1:]
            usable = [(r[0], r[1]) for r in rows if r[1] in ("200", "301")]
            ok     = [r for r in usable if r[1] == "200"]
            dates  = sorted(set(r[0][:8] for r in usable))
            return len(usable), len(ok), dates, ""
        except Exception as e:
            last_err = str(e)
            if "timed out" not in last_err.lower() and "reset" not in last_err.lower():
                break  # non-transient error; don't retry
    return 0, 0, [], last_err


# ── CSV helpers ────────────────────────────────────────────────────────────────

FIELDNAMES = [
    "app_name", "app_id", "is_ai",
    "avail_check", "avail_ts",
    "snap_count_usable", "snap_count_200only",
    "snap_dates", "passes_gate", "error"
]


def load_existing():
    done = {}
    if not os.path.exists(OUTPUT_FILE):
        return done
    with open(OUTPUT_FILE, newline="") as f:
        for row in csv.DictReader(f):
            done[row["app_id"]] = row
    return done


def append_row(row_dict, write_header=False):
    mode = "w" if write_header else "a"
    with open(OUTPUT_FILE, mode, newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_header:
            w.writeheader()
        w.writerow(row_dict)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 72)
    print("  Stage 1: Coverage Census  (v2)")
    print(f"  Window:  {WINDOW_FROM} – {WINDOW_TO}")
    print(f"  Apps:    {len(APPS)}  ({sum(a['is_ai'] for a in APPS)} AI, {sum(not a['is_ai'] for a in APPS)} control)")
    print(f"  Gate:    AI≥{MIN_AI_APPS} and Ctrl≥{MIN_CTRL_APPS} apps with ≥{MIN_SNAPS} snaps")
    print(f"  Delays:  {DELAY_BETWEEN}s between CDX; retries at {RETRY_DELAYS}s")
    est = len(APPS) * (DELAY_BETWEEN + 3)
    print(f"  Est. time: ~{est//60} min (fresh session; may be faster if Availability skips CDX)")
    print("=" * 72)

    done       = load_existing()
    first_row  = not os.path.exists(OUTPUT_FILE)
    results    = []
    skipped    = 0

    for app in APPS:
        app_id   = app["id"]
        app_name = app["name"]
        is_ai    = app["is_ai"]

        if app_id in done:
            r = done[app_id]
            cnt  = int(r["snap_count_usable"])
            cnt2 = int(r["snap_count_200only"])
            dates = r["snap_dates"].split("|") if r["snap_dates"] else []
            err   = r["error"]
            avail = r.get("avail_check", "?")
            skipped += 1
            print(f"  [cached] {app_name:<26}  snaps={cnt}")
        else:
            tag = "AI " if is_ai else "CTL"
            print(f"  [{tag}] {app_name:<26}  ", end="", flush=True)

            # Step 1: Availability API (fast, lightweight)
            avail, avail_ts = check_availability(app_id)
            time.sleep(1)  # tiny pause between avail + CDX

            if not avail:
                # No snapshot even close to Nov 2025; skip CDX
                cnt, cnt2, dates, err = 0, 0, [], "avail:none"
                print(f"avail=❌  →  0 snaps (skipped CDX)")
            else:
                print(f"avail=✅({avail_ts[:8]})  ", end="", flush=True)
                cnt, cnt2, dates, err = fetch_cdx_with_backoff(app_id)
                flag = "✅" if cnt >= MIN_SNAPS else ("⚠️ " if cnt > 0 else "❌ ")
                print(f"{flag}  {cnt} snaps  ({cnt2} HTTP-200)"
                      + (f"  ERR:{err}" if err and "avail" not in err else ""))
                time.sleep(DELAY_BETWEEN)

            row_dict = {
                "app_name":           app_name,
                "app_id":             app_id,
                "is_ai":              "1" if is_ai else "0",
                "avail_check":        "1" if avail else "0",
                "avail_ts":           avail_ts if isinstance(avail_ts, str) else "",
                "snap_count_usable":  cnt,
                "snap_count_200only": cnt2,
                "snap_dates":         "|".join(dates),
                "passes_gate":        "1" if cnt >= MIN_SNAPS else "0",
                "error":              err,
            }
            append_row(row_dict, write_header=first_row)
            first_row = False

        results.append({
            "name": app_name, "id": app_id, "is_ai": is_ai,
            "count": cnt, "count2": cnt2,
            "dates": dates, "passes": cnt >= MIN_SNAPS, "err": err,
        })

    # ── Summary ────────────────────────────────────────────────────────────────
    print()
    print("=" * 72)
    print("  COVERAGE CENSUS RESULTS")
    print("=" * 72)
    print(f"\n  {'App':<28} {'AI':>3} {'Snaps':>6} {'200s':>5}  {'Pass':>4}  Sample dates")
    print("  " + "─" * 68)

    ai_pass = ctrl_pass = 0
    for r in sorted(results, key=lambda x: (-int(x["is_ai"]), -x["count"])):
        ai_tag   = "Y" if r["is_ai"] else "N"
        pass_tag = "✅" if r["passes"] else "  "
        dates_str = ", ".join(r["dates"][:4]) + ("…" if len(r["dates"]) > 4 else "")
        print(f"  {r['name']:<28} {ai_tag:>3} {r['count']:>6} {r['count2']:>5}  {pass_tag:>4}  {dates_str}")
        if r["passes"]:
            if r["is_ai"]: ai_pass   += 1
            else:          ctrl_pass += 1

    print()
    print(f"  AI apps passing gate   (≥{MIN_SNAPS} snaps): {ai_pass:>3}")
    print(f"  Control apps passing gate (≥{MIN_SNAPS} snaps): {ctrl_pass:>3}")
    print()

    go = (ai_pass >= MIN_AI_APPS) and (ctrl_pass >= MIN_CTRL_APPS)
    if go:
        print("  ✅ STAGE GATE: GO — proceed to Stage 2")
    else:
        missing = []
        if ai_pass < MIN_AI_APPS:   missing.append(f"AI {ai_pass}/{MIN_AI_APPS}")
        if ctrl_pass < MIN_CTRL_APPS: missing.append(f"Ctrl {ctrl_pass}/{MIN_CTRL_APPS}")
        print(f"  ❌ STAGE GATE: NO-GO  ({', '.join(missing)} below threshold)")
        print("     Options: lower MIN_SNAPS, expand app list, or reframe scope")

    passing = [r for r in results if r["passes"]]
    if passing:
        print(f"\n  Apps entering Stage 2 ({len(passing)}):")
        for r in sorted(passing, key=lambda x: (-int(x["is_ai"]), -x["count"])):
            tag = "AI " if r["is_ai"] else "CTL"
            print(f"    [{tag}] {r['name']:<28} {r['count']} snaps  "
                  f"{r['dates'][0] if r['dates'] else '?'} – {r['dates'][-1] if r['dates'] else '?'}")

    print(f"\n  Results: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
