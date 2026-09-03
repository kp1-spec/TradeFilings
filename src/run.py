"""One full cycle: collect new House PTRs, rebuild the dashboard, email a digest."""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(__file__))
import house_collector, build_dashboard, send_digest

cfg = json.load(open(os.path.join(os.path.dirname(__file__), "..", "config.json")))
years = cfg.get("years") or [dt.date.today().year]

new_tx = house_collector.collect(years=years, max_new=cfg.get("max_new_filings_per_run", 200))
print(f"House: {len(new_tx)} new transactions")
n = build_dashboard.build()
print(f"Dashboard rebuilt with {n} rows")
if os.environ.get("SMTP_USER"):
    send_digest.send(new_tx)
else:
    print("SMTP_USER not set; skipping email")
