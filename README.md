name: Refresh neurocritical care jobs and deploy Cloudflare Worker

on:
  workflow_dispatch:
  schedule:
    # Every hour at :07 UTC (GitHub scheduled runs may be delayed).
    - cron: '7 * * * *'
  push:
    branches: [main]
    paths-ignore:
      - 'README.md'
      - 'CLOUDFLARE_SETUP.md'
      - 'data/jobs.json'
      - 'data/bootstrap.js'

permissions:
  contents: write

concurrency:
  group: neuro-radar-worker
  cancel-in-progress: false

jobs:
  refresh-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Check out project
        uses: actions/checkout@v4
        with:
          persist-credentials: true

      - name: Check Cloudflare configuration
        env:
          WORKER_NAME: ${{ vars.CLOUDFLARE_WORKER_NAME }}
          CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
        run: |
          test -n "$WORKER_NAME" || { echo 'Missing GitHub repository variable CLOUDFLARE_WORKER_NAME'; exit 1; }
          test -n "$CLOUDFLARE_ACCOUNT_ID" || { echo 'Missing GitHub secret CLOUDFLARE_ACCOUNT_ID'; exit 1; }
          test -n "$CLOUDFLARE_API_TOKEN" || { echo 'Missing GitHub secret CLOUDFLARE_API_TOKEN'; exit 1; }
          echo 'Cloudflare destination configured.'

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install job collector
        run: python -m pip install -r requirements.txt

      - name: Run collector tests
        run: python -m unittest discover -s tests -v

      - name: Search connected job boards
        env:
          SERPAPI_KEY: ${{ secrets.SERPAPI_KEY }}
          MAX_SERPAPI_QUERIES_PER_RUN: ${{ vars.MAX_SERPAPI_QUERIES_PER_RUN || '2' }}
          ADZUNA_APP_ID: ${{ secrets.ADZUNA_APP_ID }}
          ADZUNA_APP_KEY: ${{ secrets.ADZUNA_APP_KEY }}
          USAJOBS_API_KEY: ${{ secrets.USAJOBS_API_KEY }}
          USAJOBS_EMAIL: ${{ secrets.USAJOBS_EMAIL }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python -m collector.collect

      - name: Save detected jobs for next scan
        run: |
          git config user.name 'github-actions[bot]'
          git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
          git add data/jobs.json data/bootstrap.js
          if ! git diff --cached --quiet; then
            git commit -m 'Refresh neurocritical care jobs'
            git push origin HEAD:main
          fi

      - name: Assemble static website
        run: |
          mkdir -p dist/data
          cp index.html app.css app.js dist/
          cp data/jobs.json data/bootstrap.js data/sources.json dist/data/

      - name: Deploy to existing Cloudflare Worker
        uses: cloudflare/wrangler-action@v4
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          command: deploy --assets=./dist --name=${{ vars.CLOUDFLARE_WORKER_NAME }} --compatibility-date=2026-10-24
