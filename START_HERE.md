# Start here — one clean deployment

Your domain: **https://neuro-radar.com**  
Your existing Cloudflare Worker: **`neuro33radar`**  
GitHub repo: **https://github.com/DToth14/neurointensivist-radar**

## 1. Back up the old GitHub code

On GitHub, Code > Download ZIP, or clone it locally. Keep a copy for rollback.

## 2. Replace the old GitHub project

Prefer GitHub Desktop on your Mac. Unzip this package; copy **all contents** into the local repository root, *including the hidden `.github` directory*, replacing old files. **Delete the old `.github/workflows/refresh.yml`**. The only workflow should be `.github/workflows/radar.yml`.

On macOS Finder press **Command + Shift + .** to show hidden directories.

Commit and push to the `main` branch. A push automatically triggers the new workflow.

Do not upload the complete project ZIP directly into Cloudflare. Cloudflare receives only the generated static `dist/` assets.

## 3. Confirm GitHub secrets

Open https://github.com/DToth14/neurointensivist-radar/settings/secrets/actions

Required to deploy: `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`. The token needs Workers Scripts **Edit** access on your account. Required to scan Google Jobs: `SERPAPI_KEY`.

You can keep the old repository variable `CLOUDFLARE_WORKER_NAME`; this rebuild does not use it because `wrangler.toml` names `neuro33radar` directly.

Optional repository variable: `MAX_SERPAPI_QUERIES_PER_RUN`, set to `1` by default. Raising it spends more API calls. Optional extra API keys are documented in README.md.

## 4. Run the single workflow

Open https://github.com/DToth14/neurointensivist-radar/actions and select **Neuro Radar - hourly scan and deploy**. Click **Run workflow** on the `main` branch. It should show:

- `Run tests`
- `Scan configured job sources`
- `Save snapshot for next scan (no Git pushes)`
- `Prepare public website`
- `Deploy existing Cloudflare Worker`

No step should say `git push`. A green workflow only means the process completed; check its scan output for actual live positions.

## 5. Verify live output

Open https://neuro-radar.com/data/jobs.json; check `meta.last_scan_at`, `meta.scan_state`, `meta.monitored_sources`, and `meta.source_status`. It is normal for a successful scan to find zero relevant jobs. Look under **Source coverage** on the site for error messages.

Then visit https://neuro-radar.com/#/jobs. **The H-1B filter is under + Optional visa filter and defaults to Any sponsorship status.**

## 6. Stop the second deployment system

After step 4/5 succeeds, open Cloudflare > Workers & Pages > `neuro33radar` > Settings > Builds. If an automatic GitHub build is connected, **Disconnect** it. This leaves the Worker and domain in place; GitHub Actions Wrangler deployment continues to publish the Worker.

## Notes

- GitHub cron `7 * * * *` means :07 each hour **UTC**, which also corresponds to :07 within the hour in Eastern Time. The time itself may be delayed by GitHub.
- Monitoring all openings instantly is not possible. Only connected, accessible sources are included.
- Data history in GitHub cache is temporary; upgrade to a permanent datastore for production reliability.
- Do not paste API keys into the website, chat, or public repository.
