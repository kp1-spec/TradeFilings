"""Collect new House Periodic Transaction Reports from the Clerk of the House.

Source: https://disclosures-clerk.house.gov (official, public domain).
  Index ZIP : /public_disc/financial-pdfs/<YEAR>FD.zip  (contains <YEAR>FD.xml)
  PTR PDFs  : /public_disc/ptr-pdfs/<YEAR>/<DocID>.pdf
"""
import io
import time
import zipfile
import datetime as dt
import xml.etree.ElementTree as ET

import requests
import pdfplumber

from ptr_parser import parse_ptr_text, parse_filer
import storage

BASE = "https://disclosures-clerk.house.gov/public_disc"
HEADERS = {"User-Agent": "personal-disclosure-monitor (contact: set-in-config)"}
REQUEST_GAP_SECONDS = 1.0   # be polite to the Clerk's server


def iso(mdy):
    """'1/16/2026' -> '2026-01-16'; returns input unchanged if it does not parse."""
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(mdy.strip(), fmt).date().isoformat()
        except (ValueError, AttributeError):
            pass
    return mdy


def fetch_index(year):
    """Return a list of filing dicts from the Clerk's year-to-date XML index."""
    url = f"{BASE}/financial-pdfs/{year}FD.zip"
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        xml_name = next(n for n in z.namelist() if n.lower().endswith(".xml"))
        root = ET.fromstring(z.read(xml_name))
    filings = []
    for m in root.iter("Member"):
        g = lambda tag: (m.findtext(tag) or "").strip()
        filings.append({
            "doc_id": g("DocID"),
            "filing_type": g("FilingType"),
            "first": g("First"), "last": g("Last"),
            "prefix": g("Prefix"), "suffix": g("Suffix"),
            "state_district": g("StateDst"),
            "year": g("Year"),
            "filing_date": g("FilingDate"),
        })
    return filings


def pdf_text(pdf_bytes):
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)


def collect(years=None, max_new=200):
    """Fetch and store PTRs not yet seen. Returns the list of new transactions."""
    years = years or [dt.date.today().year]
    new_tx = []
    for year in years:
        for f in fetch_index(year):
            if f["filing_type"] != "P" or storage.seen(f["doc_id"]):
                continue
            if len(new_tx) >= max_new and max_new:
                break
            url = f"{BASE}/ptr-pdfs/{year}/{f['doc_id']}.pdf"
            time.sleep(REQUEST_GAP_SECONDS)
            r = requests.get(url, headers=HEADERS, timeout=60)
            if r.status_code != 200:
                storage.mark_seen(f["doc_id"], status=f"http_{r.status_code}")
                continue
            text = pdf_text(r.content)
            header = parse_filer(text)
            rows = parse_ptr_text(text)
            filer = header["filer_name"] or " ".join(x for x in (f["prefix"], f["first"], f["last"], f["suffix"]) if x)
            status = "parsed" if rows else ("scanned_or_unparsed" if len(text.strip()) < 200 else "no_rows")
            for row in rows:
                row["tx_date"] = iso(row["tx_date"])
                row["notified_date"] = iso(row["notified_date"])
                row.update({
                    "source": "House",
                    "filer": filer,
                    "state_district": f["state_district"] or header["district"],
                    "filing_date": iso(f["filing_date"]),
                    "doc_id": f["doc_id"],
                    "doc_url": url,
                    "collected_at": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
                })
            storage.add_transactions(rows)
            storage.mark_seen(f["doc_id"], status=status, filer=filer, doc_url=url)
            new_tx.extend(rows)
    return new_tx


if __name__ == "__main__":
    tx = collect()
    print(f"{len(tx)} new transactions")
