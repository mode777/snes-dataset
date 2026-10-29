# SNES data sources — research notes (2026-10-29)

Goal: Title, Box Art, Description, Year, Publisher/Developer (+ Genre, Screenshots).
All findings verified hands-on unless marked otherwise.

## TL;DR recommendation

You do **not** need to crawl anything for a solid dataset:

1. **Base metadata + images: Kaggle pair (CC0)** — `sergenkaraoglan/super-nintendo-entertainment-system-games` (snes.csv: title, publisher, year, developer, players, tags, description) + `...-box-art` (3,544 box art images, joinable by title).
2. **API for completeness + screenshots: IGDB** (free non-commercial, Twitch account, 4 req/s). One-time pull of all SNES games (platform 19) takes minutes.
3. **Gap-filler: OpenVGDB v29** (SQLite, offline) and **SNES Central** (crawlable, SNES-native) for serials/box scans.

GameFAQs direct crawling is effectively dead from any datacenter IP (see README) — the only thing it uniquely offered (screenshots via game pages) is better served by IGDB.

## Comparison

| Source | Type | Title | Box Art | Description | Year | Publisher/Dev | Genre | Screenshots | License / access | Freshness |
|---|---|---|---|---|---|---|---|---|---|---|
| Kaggle sergenkaraoglan ×2 | dataset | ✅ | ✅ 3,544 files | ✅ | ✅ | ✅ both | ⚠️ tags | ❌ | **CC0** | 2023 (static) |
| IGDB (Twitch) | API | ✅ | ✅ | ✅ | ✅ | ✅ both | ✅ | ✅ | free non-commercial, 4 req/s | live |
| OpenVGDB v29 | SQLite | ✅ 3,554 SNES | ✅ 75% (GameFAQs CDN URLs) | ✅ 81% | ✅ 81% | ⚠️ dev 81%, **publisher 0%** (embedded in desc text) | ✅ 81% | ❌ | unclear (open issue #43) | 2021 (retro data barely rots) |
| Nostalgia Lab / NostalgiaDB | SQLite + API | ✅ | via presigned API URLs | ✅ + long desc | ✅ (per-region) | ✅ both | ✅ | ✅ video | free, login for downloads | active (2025+) |
| ScreenScraper | API | ✅ | ✅✅ 2D/3D/textures | ✅ multi-lang | ✅ per-region | ✅ both | ✅ | ✅ + videos | free apps only, account + dev creds, daily quotas | live, huge media DB |
| TheGamesDB | API | ✅ | ✅ (focus) | ⚠️ thin | ✅ | ⚠️ | ✅ | ✅ | free key, community | live |
| MobyGames | API | ✅ | ✅ | ✅ | ✅ | ✅ full credits | ✅ | ✅ | free non-commercial key, stricter | live |
| SNES Central | crawlable site | ✅ | ✅ front+back scans per region | ❌ | ⚠️ partial | ✅ both | ✅ | ❌ | none stated — polite crawl | active (25 yrs, updated 2026) |
| karlforshaw/opengamedb | CSV | ✅ | ✅ URLs | ✅ (Wikipedia-style) | ✅ | ❌ (in desc text) | ✅ | ❌ + **scores (GameFAQs/Metacritic!)** | open CSV on GitHub | 2026-07 |
| RAWG | API | — | — | — | — | — | — | — | **avoid**: unstable since 2024, multi-day outage Aug 2026 | declining |
| Giant Bomb | API | — | — | — | — | — | — | — | **offline** during Fandom separation rebuild | — |
| GameFAQs direct | crawl | ✅ | ✅ (blocked from DC IPs) | ✅ | ✅ | ✅ | ✅ | ✅ | IP-range block on hosting providers | n/a from here |

## Details

### Kaggle pair (sergenkaraoglan) — best ready-made base
- `super-nintendo-entertainment-system-games`: `snes.csv` (2 MB) — columns:
  `Title, Publisher, Year, Languages, Developer, Players, Tags, Description, About`. ~1.7k+ rows.
- `super-nintendo-entertainment-system-box-art`: 232 MB, 3,544 images,
  `game_covers_SNES-small/` ("Cover for <Title>.png") and `game_covers_SNES_large/`
  ("<Title>.jpeg"). Join to CSV by normalized title (strip trailing spaces, case-fold —
  e.g. "seaQuest DSV .jpeg" has a stray space). CC0.
- Anonymous download works: `https://www.kaggle.com/api/v1/datasets/download/<owner>/<slug>`

### IGDB — best API (recommended for screenshots + completeness)
- Auth: Twitch developer app (client credentials), token lives ~60 days.
- Query: Apicalypse over POST, `limit 500`/request, 4 req/s. SNES platform id: **19**.
- `fields name, summary, first_release_date, cover.image_id, screenshots.image_id,
  genres.name, involved_companies.company.name, involved_companies.developer,
  involved_companies.publisher; where platforms = (19);`
- Images: `https://images.igdb.com/igdb/image/upload/t_{size}/{image_id}.jpg`
- ToS: free for non-commercial, attribution, **no bulk re-publishing** of the dataset.

### OpenVGDB v29 (verified from the actual SQLite)
- Tables: RELEASES / ROMs / SYSTEMS / REGIONS. SNES releases: 3,554.
- Coverage: cover_front 75%, description/dev/genre/date 81%, publisher 0% (but the
  description text contains "published by X" — regex-extractable).
- Cover URLs point at `gamefaqs.gamespot.com/a/box/...` — the **image CDN is also
  Cloudflare-blocked from datacenter IPs** (verified 403), fine from residential.

### Nostalgia Lab / NostalgiaDB
- Per-platform SQLite downloads (S3 presigned, 15-min links, free login) — SNES schema:
  title, genre+genre2, short + advanced description, developer, publisher,
  release_date + per-region dates, score, players, series, ROM hashes (crc/md5/sha1!).
- Media via GraphQL `imageUrl(type)` (presigned, 15 min) — hotlink-style, not bulk-friendly.

### ScreenScraper
- Richest media (box 2D/3D/textures, screenshots, videos, marquees) + multi-language
  synopses + per-region dates. API restricted to **fully free apps** (or written
  permission), needs member + developer credentials, daily quotas by member level.
- Designed for per-ROM scraping of a library, not for whole-platform dumps.

### SNES Central (crawlable, no Cloudflare)
- Per-game pages (`article.php?id=N`): US/JP/EU titles + publishers, developer, genre,
  players, special chips, serial codes, front/back box scans (`box.php?id=..&side=front`).
- No prose descriptions, no screenshots, no explicit year field on the sample page.
- Small personal site — crawl politely (1 req/s, honest UA) if at all.

### karlforshaw/opengamedb (pushed 2026-07)
- SNES CSV: `title, released, gf_score, metascore, genre, description, cover_art_url`.
- Unique value: **GameFAQs user scores + Metascores** without crawling GameFAQs.

## Suggested pipeline

1. Ingest Kaggle snes.csv + box art (CC0 base).
2. IGDB pull for SNES (platform 19) → screenshots + missing publishers/genres.
3. OpenVGDB for cover fallback + ROM-hash joins.
4. (Optional) SNES Central for serials/box scans; opengamedb for scores.
5. Join keys: normalized title + year; keep per-source IDs for re-runs.

**License caveat:** CC0 covers the *dataset packaging*, not the underlying box art
(copyrighted by publishers). Fine for personal/research use; be careful
redistributing images publicly.
