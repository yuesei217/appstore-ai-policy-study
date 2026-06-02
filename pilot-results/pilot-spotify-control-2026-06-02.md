# Spotify Control Test: Privacy Label Pre/Post Nov 13, 2025

**Run date:** 2026-06-02  
**Script:** `pilot_spotify_control.py`  
**Purpose:** Determine whether ChatGPT's Nov 13, 2025 privacy label change was Apple's platform-wide UI update or an OpenAI-specific developer action.

---

## Wayback Coverage for Spotify (id=324684580)

```bash
curl "https://web.archive.org/cdx/search/cdx?url=apps.apple.com/us/app/spotify-music/id324684580
     &output=json&from=20240101&to=20260601&fl=timestamp,statuscode&limit=100"
```

All snapshots in CDX returned HTTP 301 (redirect). Following redirects leads to the correct archived page at:
`https://web.archive.org/web/{ts}/https://apps.apple.com/us/app/spotify-music-and-podcasts/id324684580`

Snapshots used:
- **Oct 24, 2025 (pre-policy):** `20251024233024` → 856,063 bytes (HTTP 200)
- **Nov 14, 2025 (post-policy +1 day):** `20251114165516` → 835,201 bytes (HTTP 200)
- **Dec 10, 2025 (post-policy +27 days):** `20251210195738` → 840,884 bytes (HTTP 200)

---

## Raw Section Extraction

### Spotify — Oct 24, 2025 (pre-policy)

```
[Data Used to Track You] x13:
  Data Used to Track You The following data may be used to track you
  across apps and websites owned by other companies: ...

[Data Linked to You] x12:
  Data Linked to You The following data may be collected and linked
  to your identity: ...

[Data Not Linked to You] x10: PRESENT (in JSON structure)

[Data Not Collected]: ABSENT
```

### Spotify — Nov 14, 2025 (post-policy, +1 day)

```
[Data Used to Track You] x10:
  Data Used to Track You The following data may be used to track you
  across apps and websites owned by other companies: ...    ← UNCHANGED

[Data Linked to You] x10:
  Data Linked to You The following data, WHICH MAY BE COLLECTED AND
  LINKED TO YOUR IDENTITY, MAY BE USED FOR THE FOLLOWING PURPOSES:
  Third-Party Advertising ...    ← WORDING CHANGED

[Data Not Linked to You]: ABSENT    ← DISAPPEARED

[Data Not Collected]: ABSENT
```

### Spotify — Dec 10, 2025 (post-policy, +27 days)

```
[Data Used to Track You] x10: STILL PRESENT (same wording as Nov 14)
[Data Linked to You] x10: STILL PRESENT (same purpose-based wording)
[Data Not Linked to You]: ABSENT
[Data Not Collected]: ABSENT
```

---

## Comparison Table

| Section | Spotify Oct 24 | Spotify Nov 14 | Spotify Dec 10 | ChatGPT Oct 24 | ChatGPT Nov 13+ |
|---|---|---|---|---|---|
| Data Used to Track You | ✅ Present | ✅ Present | ✅ Present | ✅ Present | ❌ **Removed** |
| Data Linked to You | ✅ Present (type-format) | ✅ Present (**purpose-format**) | ✅ Present (purpose-format) | ✅ Present (type-format) | ✅ Present (purpose-format) |
| Data Not Linked to You | ✅ Present | ❌ Absent | ❌ Absent | ✅ Present | ❌ Absent |
| Data Not Collected | ❌ Absent | ❌ Absent | ❌ Absent | ❌ Absent | ❌ Absent |

---

## Interpretation

### Change 1: "Data Linked to You" wording — PLATFORM-WIDE (Apple UI update)

Both Spotify and ChatGPT changed from:
> "The following data may be collected and linked to your identity"

to:
> "The following data, which may be collected and linked to your identity, **may be used for the following purposes**"

This change affected both apps identically around Nov 13–14, 2025.  
**Conclusion: Apple rolled out a new purpose-based display format platform-wide. This wording change has NO identification power for developer compliance.**

### Change 2: "Data Not Linked to You" disappearance — AMBIGUOUS

Both Spotify and ChatGPT lost this section around Nov 13–14.  
Could be:
- (a) Apple stopped rendering empty "Data Not Linked to You" sections
- (b) Both apps independently removed data from this category
- (c) Apple's new purpose-based format merged or reorganized this category

**Conclusion: Cannot identify whether this is Apple-driven or developer-driven without more control apps. Do not use this as a treatment indicator.**

### Change 3: "Data Used to Track You" removal — CHATGPT-SPECIFIC (developer action)

| | Oct 24 | Nov 13–14 | Dec 10 |
|---|---|---|---|
| Spotify | ✅ Present | ✅ Present | ✅ Present |
| ChatGPT | ✅ Present | ❌ **Removed** | ❌ **Removed** |

Spotify maintained "Data Used to Track You" consistently before AND after the policy date.  
ChatGPT removed it on or around Nov 13, 2025.

This is **NOT a platform-wide Apple change** — if it were, Spotify would also have lost it.  
This is **developer-driven**: OpenAI specifically removed the cross-app/website tracking designation from ChatGPT's privacy label around the policy enforcement date.

"Data Used to Track You" is the most privacy-invasive Apple privacy category — it signals that an app tracks users across third-party apps and websites. Removing it means OpenAI claimed, at the disclosure level, that ChatGPT no longer engages in this form of tracking. This is directly relevant to Apple's AI Disclosure Policy, which requires consent before sharing user data with third-party AI.

---

## Research Implication: Path 1 Is Viable with Refined Treatment Indicator

**Original treatment indicator (rejected):** any structural change in privacy label format  
→ Insufficient: "Data Linked to You" wording changed for ALL apps (Apple UI update)

**Revised treatment indicator (viable):** removal of "Data Used to Track You" section  
→ Specific to ChatGPT (and potentially other AI apps), NOT platform-wide  
→ Timing coincides with Nov 13, 2025 policy enforcement  
→ Directly relevant: "Data Used to Track You" = cross-app tracking, which Apple's AI policy targets

### Next steps if proceeding to scale:

1. Check 5–10 major AI apps (Claude, Grammarly, Perplexity, Copilot, Grok, Character.AI) for "Data Used to Track You" pre/post Nov 13
2. Check 5–10 non-AI control apps (Spotify, Notion, Dropbox, Netflix, Gmail, YouTube) — expect no removal
3. Build Wayback snapshot scraper for batch retrieval
4. Assess CDX coverage depth for each app in the sample

The research question sharpens to:

> **Did AI apps that previously disclosed "Data Used to Track You" systematically remove that disclosure around Apple's Nov 13, 2025 AI disclosure policy enforcement date, while non-AI control apps did not?**

This is a cleaner, more directly policy-relevant question than the original "did any label structure change?"
