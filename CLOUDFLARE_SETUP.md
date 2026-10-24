# Cloudflare + GitHub Actions: step-by-step

This package replaces the earlier GitHub Pages deployment workflow with a **Cloudflare Pages** one. It is designed to update an existing **Cloudflare Pages Direct Upload** project (or a new one) using **GitHub Actions**.

## 1. Create the destination Cloudflare Pages project (if not already created)

In Cloudflare dashboard → Workers & Pages → Create application → Pages → Drag-and-drop / Direct Upload. Use `neurointensivist-radar` as the project name and upload the separate `Neurointensivist_Radar_Cloudflare_Upload.zip` file that was provided earlier. Note the exact Pages project name. If it is different, configure the GitHub repository variable `CLOUDFLARE_PAGES_PROJECT` with that name.

Do not use this ZIP for Cloudflare drag-and-drop: this ZIP contains the full source code and the GitHub workflow, not just static assets.

## 2. Create the GitHub repository

Go to https://github.com/new and create a repository named `neurointensivist-radar` (public or private). Unzip **this** ZIP and put all contents at the repository root, including the **hidden `.github/workflows/refresh.yml`** file. You may use GitHub Desktop: clone the empty repository, copy the extracted files into its local folder, then commit and push to `main`.

Verify that you can see `.github/workflows/refresh.yml` in the GitHub repository. The `.github` folder is essential; uploading just the ZIP as a single file will not work.

## 3. Add three required GitHub Actions secrets

Repository → Settings → Secrets and variables → Actions → Secrets → New repository secret:

* `CLOUDFLARE_ACCOUNT_ID` — from your Cloudflare dashboard's account details (not the website domain or zone ID).
* `CLOUDFLARE_API_TOKEN` — create a custom API token in Cloudflare: Account → Cloudflare Pages → Edit. Treat this token as secret.
* `SERPAPI_KEY` — from https://serpapi.com/google-jobs-api. This enables actual job searches; without it, the workflow can publish but doesn't have a live national aggregation source.

`SERPAPI_KEY` is one initial option; alternatively set `ADZUNA_APP_ID` + `ADZUNA_APP_KEY`, `USAJOBS_API_KEY` + `USAJOBS_EMAIL`, or configure hospital ATS boards in `data/sources.json`. Multiple sources improve coverage. Some services have usage charges and quotas. Never put secrets inside public source files.

If the Cloudflare Pages project name differs from `neurointensivist-radar`, add a **repository variable** (not secret) under `Settings → Secrets and variables → Actions → Variables`: `CLOUDFLARE_PAGES_PROJECT` = exact project name.

## 4. Run the action

Go to your GitHub repository → Actions → `Refresh neurocritical care jobs and deploy Cloudflare` → `Run workflow` (main) → `Run workflow`.

The action runs tests, searches configured sources, saves JSON back to GitHub, builds a `dist` directory and deploys it using Wrangler to Cloudflare Pages. Check for a green checkmark, then open your Pages URL to view it.

The scheduled scan runs at minute 17 every hour, subject to GitHub delays. GitHub disables scheduled actions in public repositories that have had no activity for 60 days; if that happens, re-enable the workflow.

## 5. Optional alerts

For Telegram notifications, add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` as repository secrets. The collector sends alerts on newly detected records when a scan succeeds. False matches are possible and complete/instant job detection cannot be guaranteed.

## Troubleshooting

- **No workflow appears:** `.github/workflows/refresh.yml` is not in the default branch (`main`). Upload the extracted folder structure, not just the ZIP.
- **Cloudflare deployment 401/403:** API token needs Account → Cloudflare Pages → Edit; verify `CLOUDFLARE_ACCOUNT_ID`.
- **Project not found:** Set `CLOUDFLARE_PAGES_PROJECT` to the exact Pages project name or create the Pages project first.
- **Git push is rejected:** The workflow requests `contents: write`. Confirm your repository's Settings → Actions → General → Workflow permissions allow read and write, and `main` is not protected from the bot's commit.
- **Site deploys but still shows sample jobs:** Check job-search API secrets and the Actions log's `Search connected job boards` step. Zero connected sources means no live search.
- **Not truly real time:** Cron polls hourly; scans can be delayed and job boards may not expose all vacancies.

Full sources, product limitations and collector details are in `README.md`.
