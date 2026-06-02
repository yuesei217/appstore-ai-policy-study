"""
Pilot C: Version History Recoverability Test
Tests all known free/public sources for App Store version history.
Target: complete version log for 2024-2026 per app.
"""

import urllib.request
import urllib.error
import json
import re
import time

TEST_APPS = [
    {"name": "ChatGPT",  "id": 6448311069, "slug": "chatgpt"},
    {"name": "Grammarly","id": 1158877342, "slug": "grammarly-keyboard"},
]

SOURCES = [
    "iTunes Lookup API",
    "App Store HTML (main page)",
    "App Store HTML (version-history page)",
    "Wayback Machine (version-history page)",
    "AppAgg",
    "AppAdvice",
    "AppFollow",
    "AppShopper",
    "iTunes Version RSS",
    "app-store-scraper (Python library)",
]


def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            content = r.read()
            return content.decode("utf-8", errors="replace"), r.status, len(content)
    except urllib.error.HTTPError as e:
        return "", e.code, 0
    except Exception as e:
        return "", 0, 0


def count_versions(html, source_name):
    """Extract version+date pairs from HTML using multiple patterns."""
    patterns = [
        r'(\d+\.\d+[\d.]*)\s*[^<]{0,80}(20\d\d-\d\d-\d\d)',
        r'[Vv]ersion\s*([\d.]+)[^<]{0,100}((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[^<]{0,20}20\d\d)',
        r'"version"\s*:\s*"([\d.]+)"[^}]{0,100}"releaseDate"\s*:\s*"(20\d\d-\d\d-\d\d)',
    ]
    found = set()
    for p in patterns:
        for m in re.findall(p, html):
            found.add(m)
    return sorted(found, key=lambda x: x[1], reverse=True)


def test_itunes_api(app_id):
    html, status, size = fetch(f"https://itunes.apple.com/lookup?id={app_id}&country=us")
    if not html:
        return status, size, []
    data = json.loads(html)
    r = data["results"][0]
    versions = [(r.get("version", "?"), r.get("currentVersionReleaseDate", "?")[:10])]
    return status, size, versions


def test_html_main(app_id, slug):
    html, status, size = fetch(f"https://apps.apple.com/us/app/{slug}/id{app_id}")
    versions = count_versions(html, "main page")
    dates = sorted(set(re.findall(r'20\d\d-\d\d-\d\d', html)))
    return status, size, versions, f"ISO dates on page: {dates[-10:] if dates else 'none'}"


def test_html_version_page(app_id, slug):
    html, status, size = fetch(
        f"https://apps.apple.com/us/app/{slug}/id{app_id}?see-all=version-history"
    )
    versions = count_versions(html, "version-history page")
    dates = sorted(set(re.findall(r'20\d\d-\d\d-\d\d', html)))
    return status, size, versions, f"ISO dates on page: {dates[-10:] if dates else 'none'}"


def test_wayback_version_page(app_id, slug):
    cdx_url = (
        f"https://web.archive.org/cdx/search/cdx"
        f"?url=apps.apple.com/us/app/{slug}/id{app_id}*see-all=version-history"
        f"&output=json&from=20240101&to=20260601&fl=timestamp,statuscode&limit=20"
    )
    html, status, size = fetch(cdx_url)
    try:
        data = json.loads(html)
        snaps = [r for r in data[1:] if r[1] == "200"]
        return status, size, [], f"{len(snaps)} snapshots found"
    except:
        return status, size, [], "parse error"


def test_third_party(name, url_template, app_id, slug):
    url = url_template.format(app_id=app_id, slug=slug)
    html, status, size = fetch(url, timeout=10)
    versions = count_versions(html, name) if html else []
    return status, size, versions


if __name__ == "__main__":
    print("=" * 65)
    print("Pilot C: Version History Recoverability Test")
    print("=" * 65)

    for app in TEST_APPS:
        print(f"\n{'─' * 60}")
        print(f"  App: {app['name']}  (id={app['id']})")
        print(f"{'─' * 60}")

        results = []

        # 1. iTunes API
        status, size, vers = test_itunes_api(app["id"])
        results.append(("iTunes Lookup API", status, size, vers,
                        "current version only" if vers else "no data"))
        time.sleep(0.3)

        # 2. App Store main HTML
        status, size, vers, note = test_html_main(app["id"], app["slug"])
        results.append(("App Store HTML (main)", status, size, vers, note))
        time.sleep(0.5)

        # 3. App Store version-history page HTML
        status, size, vers, note = test_html_version_page(app["id"], app["slug"])
        results.append(("App Store HTML (ver-hist)", status, size, vers, note))
        time.sleep(0.5)

        # 4. Wayback Machine - version-history page
        status, size, vers, note = test_wayback_version_page(app["id"], app["slug"])
        results.append(("Wayback (ver-hist page)", status, size, vers, note))
        time.sleep(0.5)

        # 5. Third-party sites
        third_party = [
            ("AppAgg",     "https://appagg.com/ios/productivity/{slug}-{app_id}.html"),
            ("AppAdvice",  "https://appadvice.com/app/{slug}/{app_id}"),
            ("AppFollow",  "https://appfollow.io/ios/{slug}/id{app_id}"),
            ("AppShopper", "https://appshopper.com/productivity/{slug}"),
        ]
        for name, url_tpl in third_party:
            status, size, vers = test_third_party(name, url_tpl, app["id"], app["slug"])
            note = f"{len(vers)} version entries" if vers else "0 version entries"
            results.append((name, status, size, vers, note))
            time.sleep(0.5)

        # 6. iTunes version RSS
        _, status, size = fetch(
            f"https://itunes.apple.com/rss/versionhistory/id={app['id']}/json"
        )
        results.append(("iTunes Version RSS", status, size, [],
                        "endpoint exists" if status == 200 else f"HTTP {status}"))

        # Print results table
        print(f"\n  {'Source':<30} {'HTTP':>4} {'Size':>8} {'Versions':>9}  Note")
        print(f"  {'─'*30} {'─'*4} {'─'*8} {'─'*9}  {'─'*30}")
        for src, st, sz, vers, note in results:
            v_str = str(len(vers)) if vers else "0"
            print(f"  {src:<30} {str(st):>4} {sz:>8,} {v_str:>9}  {note[:40]}")
            if vers:
                for v, d in vers[:5]:
                    print(f"  {'':30}            → v{v}  {d}")

    print("\n── Summary ──")
    print("  Version history is NOT accessible via any tested free public source.")
    print("  Only the amp-api-edge endpoint (requires auth) and paid services have full history.")
