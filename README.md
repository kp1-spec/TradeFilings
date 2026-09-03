# Politician trade filings monitor

Pulls Periodic Transaction Reports (stock trades) filed by members of the U.S. House
from the Clerk of the House's public index, parses them, emails you a digest, and
publishes a filterable dashboard. Runs for free on GitHub Actions every 3 hours.

Data source: https://disclosures-clerk.house.gov (official, public domain).

## Setup (about 20 minutes, no server needed)

1. Create a free GitHub account if you don't have one, then create a new repository
   (name it anything, e.g. `trade-filings`). Choose Public if you want the free
   dashboard hosting via GitHub Pages; Private also works but Pages then needs a paid plan.
2. Upload all files from this folder to the repository (drag and drop on the
   "Add file > Upload files" page works; keep the folder structure, including
   `.github/workflows/collect.yml`).
3. Email setup (Gmail): in your Google account go to Security > 2-Step Verification >
   App passwords, create one named "trade monitor", and copy the 16-character password.
   Any other mail provider works if you set SMTP_HOST and SMTP_PORT too.
4. In the repository: Settings > Secrets and variables > Actions > New repository secret:
   - `SMTP_USER` = your Gmail address
   - `SMTP_PASS` = the app password from step 3
   - `DIGEST_TO` = the address that should receive digests
5. Settings > Actions > General > Workflow permissions: choose "Read and write permissions" and save.
6. Settings > Pages > Source: "Deploy from a branch", branch `main`, folder `/docs`. Save.
   Your dashboard URL will be shown there; add it as a repository *variable*
   named `DASHBOARD_URL` (Settings > Secrets and variables > Actions > Variables) so it appears in emails.
7. Actions tab > "Collect trade filings" > Run workflow. The first run downloads every
   PTR filed so far this year (a few hundred PDFs, several minutes). Later runs only fetch new ones.

## Adjusting what you get

Edit `config.json`:
- `alert_min_amount`: transactions at or above this low-end range value are listed first in the email (default 50001).
- `watch_tickers`: e.g. `["NVDA", "AAPL"]` always flagged regardless of size.
- `years`: which index years to scan, e.g. `[2025, 2026]` to backfill last year.
- `email_when_empty`: `true` to get an email even when nothing new was filed.

The dashboard has its own filters (minimum amount, buy/sell, date, name or ticker search); those are independent of the email threshold.

## Run it on your laptop instead

    pip install -r requirements.txt
    set SMTP_USER=... SMTP_PASS=... DIGEST_TO=...   (or export on Mac)
    python src/run.py

Then open `docs/index.html` in a browser. Schedule with Task Scheduler (Windows) or
`cron` (Mac) if you prefer the laptop, but it must be on and awake at run time.

## Known limits

- Reports filed on paper are scanned images; those are recorded in the database with
  status `scanned_or_unparsed` so you can review the PDF by hand. Text extraction with OCR is a possible next step.
- A trade can legally be filed up to 45 days after it happened. The email arrives within
  3 hours of the filing appearing on the Clerk's site, not of the trade.
- Senate and executive branch filings are not collected yet (see the project plan).

## Layout

    src/house_collector.py   download index ZIP, fetch new PTR PDFs, parse, store
    src/ptr_parser.py        turns PTR text into transaction rows
    src/storage.py           SQLite database and JSON export in data/
    src/build_dashboard.py   writes docs/index.html
    src/send_digest.py       email digest
    src/run.py               runs the whole cycle
    tests/test_parser.py     parser tests: python tests/test_parser.py
