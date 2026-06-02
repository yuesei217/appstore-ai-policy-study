#!/usr/bin/env python3
"""
Spotify control test: do the same Wayback pre/post privacy label comparison
that we did for ChatGPT, but on a non-AI app (Spotify, id=324684580).

If Spotify shows the same structural change (3-section → 1-section, type→purpose)
around Nov 13, 2025, then ChatGPT's change is likely Apple's platform UI update,
not developer-driven disclosure compliance.
"""

import urllib.request
import json
import re
import time

SPOTIFY_ID = "324684580"
CHATGPT_ID = "6448311069"

DATES = {
    "pre-policy  (Oct 24, 2025)": "20251024",
    "policy-day  (Nov 13, 2025)": "20251113",
    "post-policy (Nov 25, 2025)": "20251125",
}

SECTION_HEADERS = [
    "Data Used to Track You",
    "Data Linked to You",
    "Data Not Linked to You",
    "Data Not Collected",
]


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            try:
                return raw.decode("utf-8")
            except UnicodeDecodeError:
                return raw.decode("latin-1")
    except Exception as e:
        return f"ERROR: {e}"


def find_closest_wayback_snapshot(app_id, target_date, window_days=10):
    """Find the Wayback snapshot closest to target_date within ±window_days."""
    from_ts = str(int(target_date) - window_days * 100)  # crude but works for YYYYMMDD
    to_ts   = str(int(target_date) + window_days * 100)

    cdx_url = (
        f"https://web.archive.org/cdx/search/cdx"
        f"?url=apps.apple.com/us/app/*/id{app_id}"
        f"&output=json&from={from_ts}&to={to_ts}"
        f"&fl=timestamp,statuscode&filter=statuscode:200&limit=20"
    )
    raw = fetch(cdx_url)
    if raw.startswith("ERROR"):
        return None, raw
    try:
        rows = json.loads(raw)
        if len(rows) <= 1:
            return None, "0 snapshots in window"
        # rows[0] is the header; find snapshot closest to target_date
        snaps = [(r[0], r[1]) for r in rows[1:] if r[1] == "200"]
        if not snaps:
            return None, "0 HTTP-200 snapshots"
        best = min(snaps, key=lambda x: abs(int(x[0][:8]) - int(target_date)))
        return best[0], f"{len(snaps)} snapshot(s) found; using {best[0]}"
    except Exception as e:
        return None, f"parse error: {e}"


def fetch_wayback_snapshot(ts, app_id):
    url = f"https://web.archive.org/web/{ts}/https://apps.apple.com/us/app/id{app_id}"
    raw = fetch(url, timeout=30)
    return raw, url


def extract_privacy_section(html):
    """Same extraction logic as pilot_a_privacy_labels.py."""
    if html.startswith("ERROR"):
        return {"error": html}

    result = {}
    for header in SECTION_HEADERS:
        count = html.count(header)
        if count > 0:
            idx = html.find(header)
            snippet = html[idx : idx + 400]
            # strip HTML tags for readability
            snippet = re.sub(r"<[^>]+>", " ", snippet)
            snippet = re.sub(r"\s+", " ", snippet).strip()
            result[header] = snippet[:300]

    # also count privacyTypes JSON occurrences (structured data marker)
    result["_privacyTypes_count"] = html.count('"privacyTypes"')
    result["_page_size_bytes"]    = len(html)
    return result


def summarize(sections):
    headers_found = [h for h in SECTION_HEADERS if h in sections]
    if not headers_found:
        return "  (no privacy section headers found)"
    lines = [f"  Sections: {headers_found}"]
    for h in headers_found:
        lines.append(f"  [{h}]")
        lines.append(f"    {sections[h][:200]}")
    lines.append(f"  privacyTypes occurrences: {sections.get('_privacyTypes_count', 0)}")
    lines.append(f"  page size: {sections.get('_page_size_bytes', 0):,} bytes")
    return "\n".join(lines)


def run_app(app_id, app_name):
    print(f"\n{'='*65}")
    print(f"  {app_name}  (id={app_id})")
    print(f"{'='*65}")

    results = {}
    for label, target_date in DATES.items():
        print(f"\n── {label} ──")
        ts, note = find_closest_wayback_snapshot(app_id, target_date)
        print(f"   CDX: {note}")
        if ts is None:
            print("   → No snapshot available.")
            results[label] = None
            time.sleep(1)
            continue
        html, wb_url = fetch_wayback_snapshot(ts, app_id)
        sections = extract_privacy_section(html)
        print(f"   URL: {wb_url}")
        print(summarize(sections))
        results[label] = sections
        time.sleep(2)

    return results


def compare(chatgpt_like_change, spotify_results):
    print(f"\n{'='*65}")
    print("  COMPARISON SUMMARY")
    print(f"{'='*65}")

    rows = []
    for label in DATES:
        sr = spotify_results.get(label)
        if sr is None:
            sp_sections = "N/A"
        else:
            found = [h.replace("Data ", "") for h in SECTION_HEADERS if h in sr]
            sp_sections = ", ".join(found) if found else "(none detected)"
        rows.append((label.strip(), sp_sections))

    print(f"\n{'Period':<30}  {'Spotify sections'}")
    print("-" * 65)
    for period, sp in rows:
        print(f"  {period:<28}  {sp}")

    print("\n  ChatGPT (from pilot-ac results):")
    print("    Oct 24:  Data Used to Track You + Data Linked to You + Data Not Linked to You")
    print("    Nov 13+: Data Linked to You only  (purpose-organized)")

    print("\n─── Interpretation guide ───")
    print("  If Spotify shows same 3→1 section collapse around Nov 13:")
    print("  → APPLE UI CHANGE (platform-wide format update)")
    print("  → ChatGPT's change has NO identification power for compliance")
    print()
    print("  If Spotify stays stable (3 sections before AND after):")
    print("  → DEVELOPER-DRIVEN CHANGE")
    print("  → ChatGPT's change is evidence of OpenAI updating disclosure")
    print("  → Path 1 has identification power → proceed to scale")


if __name__ == "__main__":
    print("=" * 65)
    print("  Spotify Control Test: Privacy Label Pre/Post Nov 13, 2025")
    print("  Control app: Spotify (id=324684580)")
    print("  Baseline:    ChatGPT (id=6448311069) — changed on Nov 13")
    print("=" * 65)

    spotify_results = run_app(SPOTIFY_ID, "Spotify")

    compare(None, spotify_results)

    print("\n\nOptional: also check Grammarly (id=1158877342) as a second AI-app data point")
    grammarly_results = run_app("1158877342", "Grammarly")

    print(f"\n{'='*65}")
    print("  Grammarly sections by period:")
    for label in DATES:
        gr = grammarly_results.get(label)
        if gr is None:
            print(f"    {label.strip()}: N/A")
        else:
            found = [h.replace("Data ", "") for h in SECTION_HEADERS if h in gr]
            print(f"    {label.strip()}: {found if found else '(none)'}")
