# Neurointensivist Radar — Clean rebuild (October 2026)

A public U.S. neurocritical-care **attending physician** job dashboard. The home view shows all collected physician postings. H-1B/visa filtering is available under **+ Optional visa filter**; it is **off by default**.

## Architecture

- **GitHub** stores the source code and executes a single Actions pipeline, `.github/workflows/radar.yml`.
- The pipeline searches configured job APIs at minute **:07 UTC** of every hour, publishes the generated static dashboard to the existing **Cloudflare Worker `neuro33radar`** at `neuro-radar.com`, and stores its last job snapshot in **GitHub Actions Cache**, not the `main` branch.
- **Cloudflare** serves the website. No Python scripts or API keys go to the public website.
- **No example jobs** are mixed into the live results. A scan with zero results still displays an accurate last-attempt timestamp and source diagnostics.
- **H-1B** classification requires explicit job-description wording. Unknown is not evidence of eligibility. Employers may change policies; verify every position before applying.

### Source support

SerpApi Google Jobs; optional Adzuna and USAJOBS API credentials; optional public employer ATS feeds for Greenhouse, Lever, Ashby, SmartRecruiters and selected Workday boards via `data/sources.json`. The additional physician job-board links under Sources are discovery links **not automatically crawled**.

**Limitations:** This is a monitored subset of public job postings, never a guarantee of every opening. It does not fetch jobs instantly when they are published. GitHub Actions cron can run late or be skipped. An hourly scan is not a nationwide search of every city every hour. By default, **one** SerpApi query runs per scan, rotating through city/role combinations; the current config has 20 cities and 2 terms, so a complete rotation takes roughly 40 hourly runs. Increase the `MAX_SERPAPI_QUERIES_PER_RUN` GitHub repository variable if your paid API quota allows. At one per hour this can consume ~720 calls in a 30-day month; two per hour ~1,440.

**Snapshot retention:** GitHub Actions Cache is a convenient starting point, **not a permanent database**. A cache can expire or be evicted, resetting remembered first-seen dates/history. For robust long-term tracking, replace cache with Cloudflare R2/KV/D1 or another persistent store once the first release is stable. It is not a guaranteed historical ledger.

## Installation / clean migration

Read **`START_HERE.md`** and follow the sequence. The old `.github/workflows/refresh.yml` must be deleted; keeping it causes a duplicate second workflow. Disable the old Cloudflare Git-linked auto-deploy **after** testing GitHub Actions deployment, so only one system publishes the Worker. Cloudflare's static Worker binding page does not accept secrets; API secrets belong in GitHub Actions.

## Quick local test

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m collector.collect
python -m http.server 8080
```

Open http://localhost:8080. A run without API keys reports `scan_state: unconfigured`, which is an honest configuration status rather than fake job listings.

## Required GitHub secrets

`CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` (Workers Scripts/Edit), and at least one live source key such as `SERPAPI_KEY`.

Optional: `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `USAJOBS_API_KEY`, `USAJOBS_EMAIL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`. Never commit keys in `data/`, JSON, or HTML.

The Worker name is set in `wrangler.toml` as **`neuro33radar`** so the previous `CLOUDFLARE_WORKER_NAME` variable is unnecessary in this version.

## Acceptance checklist

1. New Actions run: tests, scan, snapshot cache, build, Wrangler deploy all green.
2. Open `https://neuro-radar.com/data/jobs.json`; `meta.last_scan_at` is recent, `scan_state` reflects the real outcome, and `source_status` lists each source.
3. Open `https://neuro-radar.com/#/jobs`; LAST SCAN should show the latest attempt even if zero jobs were found.
4. Open **+ Optional visa filter**; it defaults to **Any sponsorship status**, so listings are *not* excluded without user selection.
5. Reload after another scheduled run to confirm scan timestamp changes (GitHub schedules are best-effort).
6. Confirm that Cloudflare's built-in Git deployment is not replacing the GitHub Actions deployment.
