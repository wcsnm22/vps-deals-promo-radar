# VPS Deals Radar

Independent, machine-readable tracker of VPS prices published by hosting providers.
Every number on the site is read from a provider's own public page by a deterministic
Python script — nothing is estimated, converted, or filled in by hand.

**Live site:** https://vps-deals-promo-radar.pages.dev

## What this is

- **A price tracker, not a coupon blog.** We do not write "exclusive" codes or invented discounts.
  We read the price a provider publishes on its own pricing page and show it with the source link
  and the exact UTC time it was read.
- **Zero runtime cost.** Scraping and rendering are pure Python standard library, run by GitHub
  Actions on public-repo minutes. No server, no database, no model calls, no API keys.
- **Honest gaps.** If a provider does not publish a price in a form the scraper can read, that plan
  shows no price at all. If a provider's `robots.txt` disallows the page, we skip the provider and
  record why in `data/offers.json`.

## How the pipeline works

```text
.github/workflows/update.yml  (every 6 hours + manual)
   └── python scraper.py   -> reads .ilang/site.ilang, fetches public provider pages,
   │                          checks robots.txt, writes data/offers.json
   ├── python build.py     -> renders templates/ into site/ (HTML + JSON-LD + sitemap.xml + robots.txt)
   ├── git commit          -> data/offers.json and site/ (each commit is a timestamped update)
   └── wrangler pages deploy site/  -> Cloudflare Pages
```

## Configuration lives in one file

`.ilang/site.ilang` is the single source of truth for: the brand, the niche, the locale, the
provider list (name, official site, pricing page, optional affiliate link, fetch kind, currency),
the fields extracted per offer, and the word lists that decide what counts as a plan name versus a
specification line or a cookie banner.

Both `scraper.py` and `build.py` read that file at runtime. Change one provider there and the next
run changes the site — no code edit, no redeploy of code.

## Repository layout

| Path | Role |
| --- | --- |
| `scraper.py` | Fetches public pages, extracts offers, writes `data/offers.json` |
| `build.py` | Renders `site/` from `data/offers.json` + `.ilang/site.ilang` |
| `templates/` | `index.html`, `provider.html`, `deal.html`, `compare.html` |
| `data/offers.json` | The dataset every number on the site comes from |
| `.ilang/site.ilang` | Site rules: providers, fields, word lists |
| `AGENTS.md` | Project boundaries for any AI editing this repo |
| `site/` | Build output; this is what gets deployed |

## Running it locally

```bash
python scraper.py    # writes data/offers.json
python build.py      # writes site/
```

Python 3.12+, no third-party packages required.

## Data rules

1. No price is ever invented. Missing data means the field is absent, not guessed.
2. Expired offers are not left standing in for live ones.
3. No currency conversion: EUR stays EUR, USD stays USD.
4. Scraping stays polite: one request per source per run, `robots.txt` respected, no login, no
   anti-bot circumvention, honest user agent.

## Deployment

Cloudflare Pages project `vps-deals-promo-radar`, deployed by `wrangler pages deploy` from the
workflow. The Cloudflare token lives in the repository's encrypted Actions secrets, never in code.

Site rules are described with the I-Lang protocol: see `.ilang/site.ilang` (protocol notes: ilang.ai).
