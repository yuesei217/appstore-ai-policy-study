#!/usr/bin/env python3
"""
Pilot GP-3: Variable Availability Audit — Apple App Store vs. Google Play
==========================================================================
For each target variable requested by the professor, determine:
  - Is the variable available?
  - From which source/field?
  - Is it exact or approximate?

Target variables:
  1. Developer unique ID
  2. Developer country
  3. App unique ID
  4. App first release date
  5. App category
  6. Install count
  7. Is free (price = 0)
  8. Contains ads
  9. Contains in-app purchases

Test apps:
  ChatGPT   — Apple: 6448311069 / Android: com.openai.chatgpt
  Grammarly — Apple: 1158877342 / Android: com.grammarly.android.keyboard
  Spotify   — Apple: 324684580  / Android: com.spotify.music
"""

import urllib.request
import json
import re
from google_play_scraper import app as gplay_app

TEST_APPS = [
    {"name": "ChatGPT",   "apple_id": "6448311069", "android_pkg": "com.openai.chatgpt"},
    {"name": "Grammarly", "apple_id": "1158877342", "android_pkg": "com.grammarly.android.keyboard"},
    {"name": "Spotify",   "apple_id": "324684580",  "android_pkg": "com.spotify.music"},
]

TARGET_VARIABLES = [
    "developer_id",
    "developer_country",
    "app_id",
    "first_release_date",
    "category",
    "install_count",
    "is_free",
    "contains_ads",
    "contains_iap",
]


# ── Apple App Store ────────────────────────────────────────────────────────────

def fetch_itunes(apple_id):
    url = f"https://itunes.apple.com/lookup?id={apple_id}&country=us"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())["results"][0]


def scrape_apple_developer_country(artist_id):
    """Try to scrape developer country from App Store developer page."""
    url = f"https://apps.apple.com/us/developer/id{artist_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="replace")
        # Look for country in the page
        # Apple shows seller info like "United States" in the developer page
        country_match = re.search(
            r'"sellerCountry"\s*:\s*"([^"]+)"', html
        )
        if country_match:
            return country_match.group(1), "artistPage:sellerCountry"
        # Try structured data
        country2 = re.search(r'"addressCountry"\s*:\s*"([^"]+)"', html)
        if country2:
            return country2.group(1), "artistPage:addressCountry"
        return None, "not found in HTML"
    except Exception as e:
        return None, f"error: {e}"


def extract_apple_variables(data, apple_id):
    """Extract all target variables from iTunes Lookup result."""
    artist_id = data.get("artistId")
    country, country_src = scrape_apple_developer_country(artist_id)

    # Check IAP: "inAppPurchases" or features list
    iap_field = data.get("isVppDeviceBasedLicensingEnabled")
    iap_features = "in-app-purchase" in str(data.get("features", [])).lower()
    # iTunes API does NOT reliably expose IAP; check if description mentions it
    desc = data.get("description", "")
    iap_desc = "in-app purchase" in desc.lower()

    return {
        "developer_id":       (str(artist_id), "iTunesAPI:artistId", "exact"),
        "developer_country":  (country, f"AppStorePage:{country_src}", "exact" if country else "unavailable"),
        "app_id":             (str(data.get("trackId")), "iTunesAPI:trackId", "exact"),
        "first_release_date": (data.get("releaseDate", "")[:10], "iTunesAPI:releaseDate", "exact"),
        "category":           (data.get("primaryGenreName"), "iTunesAPI:primaryGenreName", "exact"),
        "install_count":      (None, "not available", "unavailable"),
        "is_free":            (str(data.get("price", -1) == 0), "iTunesAPI:price==0", "exact"),
        "contains_ads":       (None, "not in API", "unavailable"),
        "contains_iap":       (None, "not reliably in iTunesAPI", "unavailable"),
    }


# ── Google Play ────────────────────────────────────────────────────────────────

def extract_gplay_variables(pkg):
    """Extract all target variables from google-play-scraper."""
    data = gplay_app(pkg, lang="en", country="us")

    # Developer ID: google-play-scraper returns developerId
    dev_id   = data.get("developerId") or data.get("developer")
    dev_url  = data.get("developerWebsite") or ""
    # Developer country: not a standard field — check if available
    dev_addr = data.get("developerAddress") or ""
    # Country is typically at the end of the address
    country  = None
    if dev_addr:
        # Last line of address is often the country
        lines = [l.strip() for l in dev_addr.split("\n") if l.strip()]
        country = lines[-1] if lines else None

    installs      = data.get("installs")          # e.g. "1,000,000,000+"
    installs_real = data.get("realInstalls")       # numeric if available
    contains_ads  = data.get("containsAds")
    offers_iap    = data.get("offersIAP")
    is_free       = data.get("free")
    released      = data.get("released")          # "Nov 15, 2022"
    genre         = data.get("genre")
    app_id        = data.get("appId")             # package name

    return {
        "developer_id":       (str(dev_id), "gPlayScraper:developerId", "exact"),
        "developer_country":  (
            country,
            "gPlayScraper:developerAddress (last line)",
            "exact" if country else "unavailable"
        ),
        "app_id":             (app_id, "gPlayScraper:appId (package name)", "exact"),
        "first_release_date": (str(released), "gPlayScraper:released", "exact"),
        "category":           (genre, "gPlayScraper:genre", "exact"),
        "install_count":      (
            f"{installs} (real={installs_real})",
            "gPlayScraper:installs / realInstalls",
            "approximate (bucket)" if installs and "+" in str(installs) else "exact"
        ),
        "is_free":            (str(is_free), "gPlayScraper:free", "exact"),
        "contains_ads":       (str(contains_ads), "gPlayScraper:containsAds", "exact"),
        "contains_iap":       (str(offers_iap), "gPlayScraper:offersIAP", "exact"),
    }


# ── Reporting ─────────────────────────────────────────────────────────────────

STATUS = {True: "✅", False: "⚠️", None: "❌"}


def availability_flag(value, platform):
    if value is None or value == "None" or value == "not available" or value == "unavailable":
        return "❌"
    return "✅"


def print_app_results(app_name, apple_vars, gplay_vars):
    print(f"\n  {'─'*70}")
    print(f"  {app_name}")
    print(f"  {'─'*70}")
    print(f"  {'Variable':<22} {'Apple value':<30} {'GP value':<30}")
    print(f"  {'─'*70}")
    for var in TARGET_VARIABLES:
        a_val, a_src, a_type = apple_vars[var]
        g_val, g_src, g_type = gplay_vars[var]
        a_flag = availability_flag(a_val, "apple")
        g_flag = availability_flag(g_val, "gplay")
        a_display = f"{a_flag} {str(a_val)[:26]}" if a_val else f"{a_flag} —"
        g_display = f"{g_flag} {str(g_val)[:26]}" if g_val else f"{g_flag} —"
        print(f"  {var:<22} {a_display:<30} {g_display}")


def main():
    print("=" * 72)
    print("  Pilot GP-3: Variable Availability Audit")
    print("  Apple App Store  vs.  Google Play")
    print("=" * 72)

    all_results = []

    for app in TEST_APPS:
        name = app["name"]
        print(f"\n[{name}] Fetching Apple iTunes API (id={app['apple_id']})...", end="", flush=True)
        try:
            itunes_data  = fetch_itunes(app["apple_id"])
            apple_vars   = extract_apple_variables(itunes_data, app["apple_id"])
            print(" OK")
        except Exception as e:
            print(f" ERROR: {e}")
            apple_vars = {v: (None, f"error: {e}", "error") for v in TARGET_VARIABLES}

        print(f"[{name}] Fetching Google Play (pkg={app['android_pkg']})...", end="", flush=True)
        try:
            gplay_vars = extract_gplay_variables(app["android_pkg"])
            print(" OK")
        except Exception as e:
            print(f" ERROR: {e}")
            gplay_vars = {v: (None, f"error: {e}", "error") for v in TARGET_VARIABLES}

        all_results.append((name, apple_vars, gplay_vars))
        print_app_results(name, apple_vars, gplay_vars)

    # ── Cross-app summary ──────────────────────────────────────────────────────
    print(f"\n\n{'='*72}")
    print("  CROSS-PLATFORM VARIABLE AVAILABILITY SUMMARY")
    print(f"{'='*72}")
    print()
    print(f"  {'Variable':<22} {'Apple App Store':<22} {'Google Play':<22} {'Notes'}")
    print(f"  {'─'*80}")

    var_summaries = {v: {"apple": [], "gplay": []} for v in TARGET_VARIABLES}
    for name, av, gv in all_results:
        for var in TARGET_VARIABLES:
            a_flag = availability_flag(av[var][0], "apple")
            g_flag = availability_flag(gv[var][0], "gplay")
            var_summaries[var]["apple"].append(a_flag)
            var_summaries[var]["gplay"].append(g_flag)

    NOTES = {
        "developer_id":       "Apple: numeric artistId; GP: string developerId",
        "developer_country":  "Apple: requires HTML scrape of dev page; GP: from developerAddress",
        "app_id":             "Apple: numeric trackId; GP: package name string",
        "first_release_date": "Both available via API",
        "category":           "Both available via API",
        "install_count":      "Apple: not available; GP: bucket ('1B+') + exact realInstalls",
        "is_free":            "Both: price==0 flag",
        "contains_ads":       "Apple: not in API; GP: boolean field",
        "contains_iap":       "Apple: not reliably in API; GP: boolean field",
    }

    for var in TARGET_VARIABLES:
        a_flags = var_summaries[var]["apple"]
        g_flags = var_summaries[var]["gplay"]
        a_all_ok = all(f == "✅" for f in a_flags)
        g_all_ok = all(f == "✅" for f in g_flags)
        a_disp = "✅ Available" if a_all_ok else ("⚠️ Partial" if "✅" in a_flags else "❌ Not available")
        g_disp = "✅ Available" if g_all_ok else ("⚠️ Partial" if "✅" in g_flags else "❌ Not available")
        print(f"  {var:<22} {a_disp:<22} {g_disp:<22} {NOTES.get(var,'')}")

    print()
    print("  Source fields:")
    print("  Apple: iTunes Lookup API (itunes.apple.com/lookup?id=...)")
    print("  GP:    google-play-scraper app() function")
    print("  Note:  Both sources return current/static snapshot only (not historical)")


if __name__ == "__main__":
    main()
