# Neurointensivist Radar

An open, shareable, mobile-ready US job monitor for **neurointensivist / neurocritical-care attending physician positions**. This repository contains a static website, a Python data collector and a scheduled GitHub Actions deployment. There is no login requirement for visitors.

**Important:** No provider offers a guaranteed complete/instant list of every employer's vacancies. The collector monitors **only connected sources**. It cannot magically monitor all U.S. hospitals, and a scheduled search is not an instant push notification. Initial demo records are genuine third-party listings referenced in October 2026, but their current hiring status has *not* been revalidated by the automated collector.

The included workflow `.github/workflows/refresh.yml` is configured for **Cloudflare Pages**, not GitHub Pages. Read **[`CLOUDFLARE_SETUP.md`](CLOUDFLARE_SETUP.md)** for the exact deployment procedure, repository secrets, and hourly scanning.

A successful deployment requires a Cloudflare Pages project and Cloudflare account/API-token GitHub secrets. Scanning real jobs requires at least one configured external data source (SerpApi, Adzuna, USAJOBS or an employer ATS); otherwise the site stays in sample-data mode.

### Monitoring strategy

| Source | Key required? | Coverage | Notes |
| --- | --- | --- | --- |
| Google Jobs via SerpApi | Yes | Aggregated US job listings | Search terms and geographic rotation. Paid query quota may apply. |
| Adzuna | Yes | Aggregated US jobs | API availability/quotas vary. |
| USAJOBS | Yes | Federal civilian positions | Key and registered email are both required. |
| Greenhouse | No for public boards | Direct employer published listings | Add the employer's exact board token. |
| Lever | No for public boards | Direct employer published listings | Add company board token. |
| Ashby | No for public boards | Direct employer published listings | Add company board token. |
| SmartRecruiters | No for public company postings | Direct employer postings | Add employer board token. |
| Workday | Usually public endpoint | Direct employer career feeds | Configure host, tenant, site; each employer differs. |

The Neurocritical Care Society, DocCafe, PracticeLink, PracticeMatch and NEJM are linked as **manual research portals**, *not* represented as automatically collected sources. Automatic integration of those sites would require permission, an officially supported feed or an authorized licensed API. Scraping sites that prohibit automated access is not enabled.

### Configure hospitals' direct boards

Edit `data/sources.json` (exact identifiers obtained from each employer's publicly accessible ATS job-board URL):

```json
{
  "greenhouse": ["example-hospital-board-token"],
  "lever": [],
  "ashby": [],
  "smartrecruiters": [],
  "workday": [
    { "name": "Example Health", "host": "hospital.wd5.myworkdayjobs.com", "tenant": "hospital", "site": "External" }
  ],
  "serpapi_queries": [
    "neurocritical care physician",
    "neurointensivist",
    "neurocritical care medical director",
    "neuro ICU intensivist"
  ],
  "serpapi_regions": ["United States", "New York, New York", "Chicago, Illinois", "Dallas, Texas", "Los Angeles, California"]
}
```

This is a **configuration example only**: the `example-hospital-board-token` and `hospital.wd5...` entries are placeholders, *not real boards*. Do not paste examples without replacing them. The actual package starts with empty ATS lists and does not falsely claim to connect to a specific hospital.

`MAX_SERPAPI_QUERIES_PER_RUN` controls Google Jobs queries per scan (default **2**); the engine rotates query/region combinations on each hourly run. At default hourly scheduling, 2 queries per scan can consume **up to ~1,440 queries over 30 days** (more if manually triggered). Adjust your query budget and provider plan before enabling automation. Regions and result ranking can omit jobs. Additional coverage requires broader configurations and recurring source checks.

### Local preview and development

The file `index.html` can be opened directly, showing starter records from `data/bootstrap.js` when `fetch` is blocked by local-file restrictions. To run with a web server:

```bash
python -m pip install -r requirements.txt
python -m http.server 8000
# Open http://localhost:8000
```

Run a live scan after supplying at least one credential or board:

```bash
export SERPAPI_KEY='your-key-here'
python -m collector.collect
```

Use `python -m unittest discover -s tests -v` to run basic filter/normalization tests. The collector persists state in `data/jobs.json`; it retains first-detected dates, marks previously-seen vacancies as not recently seen, drops records after 45 days without fresh detection, and retains startup examples labelled "unverified" until they age out. It does **not** verify whether every externally linked employer posting remains open.

### Design and controls

- National fuzzy text search with state, physician role category, last-detected date and sort filters.
- New findings within seven days of first discovery; save jobs in local browser storage.
- Link directly to original listings, share the filtered dashboard URL, export results as CSV.
- Dashboard metrics, state/category charts, source health and first/last observed timestamps.
- Physician-only title/description filtering that excludes advanced-practice, nursing and fellowship posts. Some ambiguous roles may still require manual review.
- Uses HTML/CSS/vanilla JS and Python requests, with no server needed for viewing the public page.

### Future improvements

The optional Telegram integration sends notifications for new positions detected during scheduled scans. For genuine event-driven notifications, a source must support webhooks or another push mechanism; scheduled detection cannot guarantee instant delivery. The site itself does not send notifications from a visitor's browser. If near-real-time coverage is essential, host the collector on a background worker and pay for direct licensed provider data feeds; even then, each publisher's indexing latency and access rules determine what can be detected. Do not advertise "every job" or "instant alerts" without an audited feed inventory.

### Sources and platform documentation

- [Neurocritical Care Society careers](https://www.neurocriticalcare.org/Resources-Publications/Career-Center)
- [DocCafe neurocritical care physician jobs](https://www.doccafe.com/physician-jobs/specialty/neurocritical-care)
- [SerpApi Google Jobs API](https://serpapi.com/google-jobs-api)
- [Greenhouse public job board API](https://docs.greenhouse.io/job-board)
- [USAJOBS API](https://developer.usajobs.gov/api-reference/get-api-search)
- [GitHub Pages publishing using Actions](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)

© 2026. This project is provided as a starter application, not a guarantee of coverage, employment, medical credentialing or hiring.
