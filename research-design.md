# Research Design: Apple App Store AI Disclosure Policy Study

**Last updated:** 2026-06-02  
**Status:** Control test complete — Path 1 treatment indicator validated; ready to scale

---

## 1. Background and Motivation

On **November 13, 2025**, Apple introduced a new App Store requirement: apps that share user data with third-party AI services must obtain explicit user consent and disclose this practice. This policy creates a well-defined, externally imposed regulatory shock — a rare opportunity to study how platform-level AI governance affects app developers, app performance, and user behavior.

The central challenge of this study is not analytical but **empirical**: the key outcome variables (ratings, rankings, user reviews) are either not historically archived by Apple or only partially recoverable. This means the first task is not to collect data, but to determine whether a causal study is feasible at all.

---

## 2. Research Questions

**Primary question:**  
Did Apple's November 2025 AI disclosure requirement affect the performance, update behavior, or user reception of affected apps?

**Secondary questions:**  
- Did apps subject to the policy update more or less frequently after the policy took effect?  
- Did user sentiment shift — positively (trust restored) or negatively (inconvenience, abandonment)?  
- Did developers of affected apps release fewer new apps in the post-policy period?  
- Are smaller developers disproportionately affected compared to large ones?

---

## 3. Identification Strategy

### 3.1 Policy as a Natural Experiment

The November 13, 2025 policy date serves as an exogenous cutoff. We use a **Difference-in-Differences (DiD)** design:

```
Estimand = (Treatment_after − Treatment_before) − (Control_after − Control_before)

Pre-period:   August – November 12, 2025
Post-period:  November 14, 2025 – February 2026

Treatment group: Apps that share user data with third-party AI
Control group:   Apps with no third-party AI data sharing
```

### 3.2 Treatment Group Definition

**Critical distinction:** The policy targets apps that *share user data with third-party AI*, not merely apps that *have AI features*. On-device AI (e.g., Apple Intelligence, CoreML) is not subject to this requirement. Misidentifying treatment based on AI feature keywords would introduce substantial measurement error.

**Preferred identification approach:**  
Use the App Store **Privacy Nutrition Label** (`privacyTypes` field or equivalent) to identify apps that declare third-party AI data sharing. An ideal treatment indicator would be:

```
Treatment_i = 1  if app i disclosed AI-related third-party data sharing
```

A stronger version that captures the policy shock directly:

```
NewlyAffected_i = 1  if app i's privacy label changed around November 2025
                      to add AI-related third-party data sharing disclosure
```

**Fallback approach (if Privacy Labels are not programmatically accessible):**  
Keyword-based classification using app descriptions, update notes, or metadata — but with explicit acknowledgment that this identifies "has AI features" rather than "shares user data with third-party AI."

### 3.3 Temporal Problem in Treatment Identification

Even if Privacy Nutrition Labels are accessible today, they reflect the **current (post-policy) state**. Observing *which apps changed* their labels around November 2025 requires historical label data — which may not be recoverable. This is the same problem as historical rankings. If historical label data is unavailable, the treatment definition will be cross-sectional (current disclosure status), introducing survivorship bias: apps that exited the market after the policy cannot be observed.

---

## 4. Key Variables

### 4.1 Stable Identifiers (time-invariant)

| Variable | Field Name | Source | Notes |
|---|---|---|---|
| App unique ID | `trackId` | iTunes API | Primary key |
| Developer unique ID | `artistId` | iTunes API | Primary key |
| Bundle ID | `bundleId` | iTunes API | Technical identifier |
| First release date | `releaseDate` | iTunes API | Used for developer-level analysis |
| App category | `primaryGenreName` | iTunes API | Used for matching/controls |

### 4.2 Performance Variables (require repeated snapshots or historical recovery)

| Variable | Source | Historical Availability | Risk |
|---|---|---|---|
| Average user rating | iTunes API | No — current snapshot only | High |
| Total rating count | iTunes API | No — current snapshot only | High |
| Daily/weekly rating increment | Derived from snapshots | Only from collection date forward | High |
| Category ranking | App Store charts | No public API; requires third-party data | Critical |
| Overall ranking | App Store charts | Same as above | Critical |

**Note on ratings:** While Apple does not provide a rating history API, the `userRatingCount` field combined with review timestamps can serve as an indirect proxy for activity levels in a given period.

### 4.3 Version Update History

| Variable | Notes |
|---|---|
| Version number | Current version available via iTunes API; historical requires archival sources |
| Release date per version | Same constraint |
| Release notes per version | Same constraint |
| Update frequency | Derivable if version history is complete |

Target: **complete version history for 2024–2026** for each app in the sample.

### 4.4 User Reviews (the most critical variable)

| Variable | Source | Key Constraint |
|---|---|---|
| Review ID | App Store RSS API | Unique identifier |
| Review date (timestamp) | App Store RSS API | Core temporal variable |
| Star rating | App Store RSS API | 1–5 |
| Review title and text | App Store RSS API | Used for sentiment analysis |
| App version at time of review | App Store RSS API | Available in some storefronts |
| Country/storefront | API parameter | Varies by region |

**Critical limitation:** The public App Store RSS review feed returns approximately the **500 most recent reviews** per app. For high-volume apps (thousands of reviews per month), reviews from the November 2025 policy window may already be entirely displaced. This is the single most important feasibility question for the study.

---

## 5. Pilot Design: Feasibility Validation

Before any large-scale data collection, we must answer four binary feasibility questions. These are **Go/No-Go criteria** for the study, not preliminary steps. The pilot uses a fixed set of test apps across size tiers.

### Test App Sample (Locked)

| Tier | App | Rationale |
|---|---|---|
| Large AI | ChatGPT | Definite treatment; extremely high review volume; best stress test for RSS window |
| Medium AI | Grammarly | AI features are core product, not peripheral; review volume ~1 order of magnitude below ChatGPT |
| Small AI | TBD — AI writing / PDF summary / email assistant | Target: <200 reviews/month; selected at search time |
| Large Control | Spotify | Global review volume comparable to ChatGPT; US storefront; no third-party AI data sharing |
| Small Control | TBD — calculator / unit converter / to-do app | Target: <200 reviews/month; matched to Small AI tier |

*Small AI and Small Control apps are selected during Pilot B execution via iTunes Search API, choosing the first qualifying app by review count.*

### Pilot A — Privacy Label Feasibility *(COMPLETED 2026-06-02)*

**Question:** Can Privacy Nutrition Labels be retrieved programmatically, and can historical states be recovered?

**A1 — Current labels:**

| Method | Result | Notes |
|---|---|---|
| iTunes Lookup API | ❌ Not available | 44 fields returned; none are privacy labels |
| App Store HTML scraping | ✅ Viable | Server-side rendered; "Data Linked to You" sections with categories extractable |
| Apple amp-api-edge (`extend=privacyDetails`) | ❌ Blocked | Requires runtime bearer token; not in static HTML or JS bundles |

Extracted current state for ChatGPT (Jun 2026):
```
Data Linked to You → Third-Party Advertising: Usage Data, Product Interaction, Advertising Data
                   → Developer's Advertising: Contact Info (Email Address)
                   → Analytics: Health & Fitness, Contact Info
```

**A2 — Historical labels via Wayback Machine:**

| App | Snapshots in Oct–Dec 2025 |
|---|---|
| ChatGPT | **99** (incl. exact policy date Nov 13 at 16:14 UTC) |
| Grammarly | 0 |
| AI Writer: Email Letter | 1 (Oct 12 only) |

Pre/post-policy comparison (ChatGPT):

| Date | Sections present | Organization |
|---|---|---|
| Oct 24, 2025 (pre) | Data Used to Track You + Data Linked to You + Data Not Linked to You | By data type |
| Nov 13, 2025 (policy day) | Data Linked to You only | By purpose (Analytics → Contact Info, User Content…) |
| Nov 25, 2025 (post) | Data Linked to You only | Same as Nov 13 |

The label structure changed on/around Nov 13. Cause is ambiguous: could be Apple's new display format rolled out platform-wide, OR OpenAI updating its label content. A Spotify pre/post comparison is needed to distinguish.

**Verdict:** A1 ✅ viable via HTML scraping. A2 ⚠️ viable only for top ~50–100 apps with dense Wayback coverage.

→ Full raw output and evidence: [pilot-results/pilot-ac-2026-06-02.md](pilot-results/pilot-ac-2026-06-02.md)

### Pilot B — Review Recoverability *(COMPLETED 2026-06-02)*

**Question:** Do reviews from the November 2025 policy window still exist in the RSS feed?

**Method:** Paginated App Store RSS review feed (up to 10 pages × 50 = 500 max), `sortBy=mostRecent`, US storefront.

**Results:**

| App | Tier | Latest Review | Earliest Review | Total Returned | Days Covered | Rev/day | Nov 2025? |
|---|---|---|---|---|---|---|---|
| ChatGPT | Large AI | 2026-05-31 | 2026-05-31 | 50 | 1 | 50.0 | **NO** |
| Grammarly | Medium AI | 2026-05-31 | 2026-05-20 | 50 | 10 | 5.0 | **NO** |
| AI Writer: Email Letter | Small AI | — | — | 0 | — | — | **NO** |
| Spotify | Large Control | 2026-05-31 | 2026-05-31 | 50 | 1 | 50.0 | **NO** |
| Units - Pro Unit Converter | Small Control | — | — | 0 | — | — | **NO** |

**Diagnostic findings:**
- RSS pagination is broken: `<link rel="next" href="">` returns empty for all apps. The feed is limited to a single page (50 reviews max), not the historically documented 500.
- Small apps (AI Writer, Units Converter) return 0 entries. Likely explanation: US-storefront reviews are too sparse for RSS to populate, or Apple no longer serves RSS for low-traffic apps.
- Best earliest date reached: **2026-05-20** (Grammarly) — 6+ months after the policy date.

**Verdict: RED**  
No app reaches November 2025. Review-based DiD analysis is not viable via the public RSS API. The RSS feed has been effectively deprecated as a data source for historical research.

→ Full raw output and diagnostic evidence: [pilot-results/pilot-b-2026-06-02.md](pilot-results/pilot-b-2026-06-02.md)

### Pilot C — Version History Recoverability *(COMPLETED 2026-06-02)*

**Question:** Can complete version histories (2024–2026) be recovered for sampled apps?

**Results (tested on ChatGPT + Grammarly):**

| Source | HTTP | Size | Version Entries | Notes |
|---|---|---|---|---|
| iTunes Lookup API | 200 | 8KB | **1** (current only) | `currentVersionReleaseDate` only |
| App Store HTML (main page) | 200 | 733KB | 1 (current) | Version history JS-loaded; not in HTML |
| App Store `?see-all=version-history` | 200 | 733KB | 1 (current) | Same HTML; `fetchStrategy: "onPageLoad"` |
| Wayback Machine (ver-history page) | — | — | 0 | 0 snapshots of version-history page |
| AppAgg | 200 | 3KB | 0 | Page exists but no version data |
| AppAdvice | 0 | — | 0 | Connection blocked |
| AppFollow (public) | 200 | 104KB | 0 | Page loads but no version entries |
| AppShopper | 200 | 346KB | 0 | Page loads but no version entries |
| iTunes Version RSS | 400 | — | — | Endpoint does not exist |
| app-store-scraper (Python) | — | — | 0 | Library supports reviews only |
| amp-api-edge (`extend=versionHistory`) | — | — | — | Has data; requires runtime bearer token |

**Verdict: NOT ACCESSIBLE (free tier)**  
Version history requires either (a) Apple amp-api with a bearer token, or (b) a paid third-party service. All tested free public sources return 0 historical entries.

→ Full raw output and evidence: [pilot-results/pilot-ac-2026-06-02.md](pilot-results/pilot-ac-2026-06-02.md)

### Pilot D — Historical Ranking Availability *(COMPLETED 2026-06-02)*

**Question:** Does any accessible source provide App Store ranking history covering the November 2025 period?

**Results:**

| Source | Nov 2025 Coverage | Granularity | Free? | Notes |
|---|---|---|---|---|
| iTunes RSS (current) | ❌ Real-time only | — | Yes | `/date=` parameter is silently ignored |
| iTunes RSS `/date=` param | ❌ Returns today's data | — | Yes | Confirmed false positive; date ignored |
| **Wayback Machine — iTunes chart RSS** | **⚠️ 2 snapshots (Nov 21)** | **Sparse** | **Yes** | **Real data; top-100 apps parseable** |
| Wayback Machine — App Store charts page | ❌ 0 snapshots | — | Yes | Not archived |
| AppFollow (public) | ❌ 404 | — | — | URL no longer valid |
| Sensor Tower | ✅ Daily | Daily | No | ~$1,000+/month |
| AppTweak | ✅ Daily | Daily | Trial only | ~$500+/month |
| Appfigures | ✅ Daily | Daily | Limited | ~$100–500/month |
| data.ai / Apptopia | ✅ Daily | Daily | No | Enterprise pricing |

**Key diagnostic — Wayback Machine chart coverage (Jan 2024–Jun 2026):**
```
202401 █(1)  202403 ██(2)  202404 ██(2)  202407 ██(2)  202411 █(1)
202504 █(1)  202507 ███(3) 202508 ██(2)  202509 █(1)   202511 ██(2) ← policy window
202604 █(1)  202605 ██(2)
Total: 20 snapshots across 2.5 years
```

The Nov 21, 2025 snapshot was fetched and verified: complete top-100 list with correct app IDs (ChatGPT #1 confirmed). Data is real and parseable.

**Revised verdict: SPARSE (not paid-only)**  
Wayback has genuine iTunes chart data but only 20 point-in-time snapshots over 2.5 years. Suitable for crude pre/post snapshot comparisons; not sufficient for panel or event-study analysis. Rigorous daily ranking data still requires paid source.

→ Full raw output and evidence: [pilot-results/pilot-d-2026-06-02.md](pilot-results/pilot-d-2026-06-02.md)

### Pilot Execution Order

```
Day 1:  Run Pilot B + Pilot D in parallel
        → These are binary, fast, and gate everything else

Day 2+: Run Pilot A (Privacy Labels)
        → Results shape treatment definition

Day 3+: Run Pilot C (Version History)
        → Only meaningful if treatment can be identified
```

---

## 6. Proposed Data Schema

### `app_snapshot` — collected on a rolling basis going forward

```
snapshot_date, country, app_id, developer_id, app_name, category,
price, average_rating, rating_count, current_version,
current_version_release_date, rank_overall, rank_category,
privacy_label_raw, description_hash
```

### `app_version_history`

```
app_id, version, release_date, release_notes, source, scraped_at
```

### `app_reviews`

```
app_id, country, review_id, review_date, rating,
title, content, app_version, scraped_at
```

### `developer`

```
developer_id, developer_name, developer_url,
app_count, first_seen_date
```

---

## 7. Research Path Decision (Final — Post All Pilots + Control Test, 2026-06-02)

All four pilots and the Spotify control test are complete. Below is the full feasibility matrix and the resulting path forward.

### Feasibility Matrix

| Variable | Free / Public | Verdict | Blocker |
|---|---|---|---|
| App metadata (ID, releaseDate, genre) | iTunes API | ✅ | None |
| Current privacy labels | HTML scraping | ✅ | None |
| Historical privacy labels (pre-Nov 2025) | Wayback Machine | ⚠️ Top ~50–100 apps only | Sparse coverage for most apps |
| User reviews with timestamps | App Store RSS | ❌ | RSS capped at 50 reviews; pagination gone |
| Version update history | All tested sources | ❌ | No free source; requires amp-api auth or paid service |
| Ranking history (top-100 snapshots) | Wayback Machine | ⚠️ Sparse | 20 snapshots across 2.5 years; 2 in Nov 2025 (Nov 21) |
| Ranking history (daily, continuous) | iTunes / public | ❌ | Paid-only (Sensor Tower etc.) |

### Decision Tree

```
All 4 pilots complete (2026-06-02):

Reviews  → ❌ RED         Version History → ❌ Not accessible
Rankings → ⚠️ Sparse      Privacy Labels  → ✅ VIABLE (control test passed)

                         ↓
         Viable free-tier variable: PRIVACY LABEL CHANGES
         (treatment indicator refined — see Spotify control test below)

                         ↓
              Two realistic paths forward:
              ┌──────────────────────────────────┐
              │ Path 1: Privacy-Label Study       │  ← recommended
              │ (free; top-app sample only)       │
              └──────────────────────────────────┘
              ┌──────────────────────────────────┐
              │ Path 2: Buy review/version data   │
              │ (paid; restores fuller design)    │
              └──────────────────────────────────┘
```

### Spotify Control Test Result (2026-06-02) — Treatment Indicator Validated

**Test:** Compare Spotify's Wayback privacy label snapshots at Oct 24, Nov 14, and Dec 10, 2025 against ChatGPT's known changes. Full results: [pilot-results/pilot-spotify-control-2026-06-02.md](pilot-results/pilot-spotify-control-2026-06-02.md)

| Section | Spotify Oct 24 | Spotify Nov 14 | Spotify Dec 10 | ChatGPT Oct 24 | ChatGPT Nov 13+ |
|---|---|---|---|---|---|
| Data Used to Track You | ✅ Present | ✅ Present | ✅ Present | ✅ Present | ❌ **Removed** |
| Data Linked to You | ✅ (type-format) | ✅ (purpose-format) | ✅ (purpose-format) | ✅ (type-format) | ✅ (purpose-format) |
| Data Not Linked to You | ✅ Present | ❌ Absent | ❌ Absent | ✅ Present | ❌ Absent |

**Finding: Two distinct changes happened around Nov 13, 2025:**

1. **Platform-wide Apple UI update (both apps affected):**
   - "Data Linked to You" wording changed from "may be collected and linked to your identity" → "may be used for the following purposes" (purpose-based format)
   - "Data Not Linked to You" disappeared from both Spotify and ChatGPT
   - This is NOT usable as a treatment indicator — it affected all apps

2. **ChatGPT-specific developer action:**
   - "Data Used to Track You" was **removed only from ChatGPT**, not from Spotify
   - Spotify maintained this section consistently before and after Nov 13
   - This is directly relevant to Apple's policy: "Data Used to Track You" = cross-app/website tracking, which AI disclosure policy targets
   - Removal indicates OpenAI specifically updated their privacy disclosure around the policy date

**Refined treatment indicator:**

```
Treatment_i = 1  if "Data Used to Track You" was present before Nov 13
                     AND absent on/after Nov 13 in app i's privacy label
```

This indicator is:
- Observable via Wayback Machine for top apps
- NOT confounded by Apple's platform-wide UI update (Spotify kept it)
- Directly relevant to the policy mechanism (cross-app tracking disclosure)
- Falsifiable: control apps should show no removal; AI apps should show removal if complying

**Sharpened research question:**
> Did AI apps that previously disclosed cross-app user tracking ("Data Used to Track You") systematically remove that disclosure around Apple's Nov 13, 2025 AI disclosure policy, while non-AI control apps did not?

### Path 1 — Privacy Label Compliance Study *(recommended free-tier path)*

**What's feasible:**  
Wayback Machine has dense coverage (50–200+ snapshots) for top apps during Oct–Dec 2025. Privacy label HTML is preserved server-side. Spotify control test confirms "Data Used to Track You" removal is app-specific, not a platform artifact.

**Research design:**
- **Sample**: ~50–150 apps with dense Wayback coverage; top AI apps (ChatGPT, Claude, Grammarly, Perplexity, Copilot, Grok, Character.AI) + matched non-AI control apps (Spotify, Notion, Netflix, Gmail, YouTube, Dropbox)
- **Treatment indicator**: removal of "Data Used to Track You" section on/after Nov 13, 2025
- **Outcomes**:
  - Binary: did the app remove "Data Used to Track You" post-policy? (1/0)
  - Timing: how many days after Nov 13 did the removal appear in the label?
  - Additional: were new categories added to "Data Linked to You" (expanded disclosure)?
- **Research question**: *Among top apps that previously disclosed cross-app tracking, did AI apps remove that disclosure around the Nov 13 policy at higher rates than non-AI apps?*
- **Key limitation**: sample restricted to apps popular enough for Wayback crawling; results do not generalize to long-tail developers

**Next step to proceed:** Build CDX coverage list for the target ~50 apps; batch scrape Wayback snapshots in Oct–Dec 2025 window.

### Path 2 — Full DiD with Paid Data *(restores original design)*

If budget is available, the following paid sources restore the key missing variables:

| Variable | Source | Est. Cost |
|---|---|---|
| Review history (Aug 2025–Feb 2026) | AppFollow, Appfigures, Apptopia | $500–2,000 (one-time pull) |
| Version history (2024–2026) | Appfigures, Sensor Tower | Included in review subscriptions |
| Ranking history | Sensor Tower, AppTweak | $500–1,000+/month |

With review + version history: full DiD around Nov 13, 2025 with developer behavior AND user reaction outcomes becomes feasible.

---

## 8. Key Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Review RSS window too short to reach Nov 2025 | Critical | Test in Pilot B before any other work |
| No programmatic access to Privacy Nutrition Labels | High | Test HTML extraction; consider browser automation |
| Ranking history unrecoverable without paid source | High | Quantify cost in Pilot D; drop ranking if cost prohibitive |
| Version history sparse from public sources | Medium | Aggregate multiple archival sources |
| Treatment/control misclassification | High | Document classification method; conduct sensitivity analysis |
| Survivorship bias (exited apps invisible) | Medium | Acknowledge in limitations; consider App Store removals as a separate outcome |
| Apple API rate limits or structure changes | Low-Medium | Implement polite crawling; cache all raw responses |

---

## 9. Next Steps (Updated 2026-06-02 — Control Test Complete)

**All pilots + control test completed:**
- [x] Pilot B — Reviews → **RED** → [pilot-results/pilot-b-2026-06-02.md](pilot-results/pilot-b-2026-06-02.md)
- [x] Pilot D — Rankings → **Sparse (not paid-only)** → [pilot-results/pilot-d-2026-06-02.md](pilot-results/pilot-d-2026-06-02.md)
- [x] Pilot A — Privacy Labels → **A1 viable; A2 conditional (top apps only)** → [pilot-results/pilot-ac-2026-06-02.md](pilot-results/pilot-ac-2026-06-02.md)
- [x] Pilot C — Version History → **NOT ACCESSIBLE (free tier)**
- [x] Spotify control test → **PASSED: treatment indicator validated** → [pilot-results/pilot-spotify-control-2026-06-02.md](pilot-results/pilot-spotify-control-2026-06-02.md)

**Treatment indicator confirmed:** removal of "Data Used to Track You" around Nov 13, 2025 is app-specific (not platform-wide Apple UI change). Path 1 is viable.

**If proceeding with Path 1 (free tier — recommended):**
1. Build CDX coverage list: query Wayback CDX for ~50 target apps (AI apps + controls), record snapshot counts in Oct–Dec 2025 window
2. Shortlist to apps with ≥3 snapshots in the policy window (pre + on-date + post)
3. Write batch Wayback scraper: for each app, retrieve Oct and Dec 2025 snapshots and extract "Data Used to Track You" presence/absence
4. Encode treatment indicator: `track_removed = 1/0` per app
5. Descriptive: treatment rate in AI vs. non-AI apps; timing distribution
6. If sufficient variation: run event-study with day-of-removal as outcome

**If proceeding with Path 2 (paid data):**
1. Request quotes from AppFollow / Appfigures for review + version history pull
2. Define exact app list and time range before purchasing
3. Re-run full DiD design with reviews + version history as outcomes; privacy label change as treatment indicator
