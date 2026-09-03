"""Parse the text of a House Periodic Transaction Report (PTR) into transaction rows.

Works on the text extracted from electronically filed PTR PDFs. Each transaction
line looks like one of these (amount ranges sometimes wrap to the next line):

  SP Apple Inc. - Common Stock (AAPL) [ST] P 12/22/2023 12/22/2023 $1,000,001 - $5,000,000
  Treaty Energy Corporation (TECO) s 07/1/2016 08/6/2016 $1,001 - $15,000        (older layout)

The parser anchors on the "(TICKER) [TYPE] P|S|E date date $low - $high" marker,
then walks backward for the asset name.
"""
import re

OWNER_CODES = {"SP": "Spouse", "DC": "Dependent child", "JT": "Joint", "": "Self"}

# Ticker in parentheses, optional asset-type bracket, transaction code, two dates, amount range.
ROW_RE = re.compile(
    r"\(([A-Z0-9.\-/ ]{1,12}|--)\)\s*"            # (AAPL) or (--)
    r"(?:\[([A-Z]{2,3})\]\s*)?"                     # optional [ST]
    r"(P|S\s*\(partial\)|S|E)\s+"                   # transaction type
    r"(\d{1,2}/\d{1,2}/\d{4})\s+"                   # transaction date
    r"(\d{1,2}/\d{1,2}/\d{4})\s+"                   # notification date
    r"\$([\d,]+)\s*-\s*(?:Yes|No)?\s*\$([\d,]+)",   # amount range (cap-gains Yes/No may sit inside)
    re.IGNORECASE,
)

# Text between rows that is not part of an asset name.
NOISE_RE = re.compile(
    r"(TRANSACTIONS|ID\s+Owner\s+Asset\s+Transaction(?:\s+Type)?\s+Date\s+Notification(?:\s+Date)?\s+Amount(?:.*?\$200\?)?|Cap\.|Gains\s*>|"
    r"FILING STATUS.*|"
    r"\bYes\b|\bNo\b|Page \d+ of \d+)",
    re.IGNORECASE,
)


def _to_int(s):
    return int(s.replace(",", ""))


def _clean_asset(raw):
    raw = NOISE_RE.sub(" ", raw)
    raw = re.sub(r"\s+", " ", raw).strip(" -:")
    owner = ""
    m = re.match(r"^(SP|DC|JT)\s+", raw)
    if m:
        owner = m.group(1)
        raw = raw[m.end():]
    # If a description or comment from the previous row bled in, keep only the
    # part after it (the asset name always sits right before the ticker).
    parts = re.split(r"(?:\b(?:Description|Comments?)|\bD|\bF S|\bC):", raw, flags=re.IGNORECASE)
    raw = parts[-1]
    if len(parts) > 1 and ". " in raw:
        # A free-text note preceded this asset; keep what follows its last sentence.
        raw = raw.rsplit(". ", 1)[-1]
    raw = re.sub(r"\s+", " ", raw).strip(" -:")
    m = re.match(r"^(SP|DC|JT)\s+", raw)
    if m and not owner:
        owner = m.group(1)
        raw = raw[m.end():]
    if len(raw) > 120:
        raw = raw[-120:].lstrip()
    return owner, raw


def parse_ptr_text(text):
    """Return a list of transaction dicts found in PTR text."""
    flat = re.sub(r"\s+", " ", text.replace("\x00", " "))
    # Everything before the transactions table is filer info; drop it.
    start = flat.upper().find("TRANSACTIONS")
    body = flat[start:] if start >= 0 else flat

    rows = []
    prev_end = 0
    for m in ROW_RE.finditer(body):
        owner, asset = _clean_asset(body[prev_end:m.start()])
        ttype = m.group(3).upper().replace(" ", "")
        if ttype.startswith("S"):
            ttype = "S (partial)" if "PARTIAL" in ttype else "S"
        rows.append({
            "owner": OWNER_CODES.get(owner, owner),
            "asset": asset,
            "ticker": None if m.group(1) == "--" else m.group(1).upper(),
            "asset_type": (m.group(2) or "").upper() or None,
            "tx_type": {"P": "Buy", "S": "Sell", "S (partial)": "Sell (partial)", "E": "Exchange"}[ttype],
            "tx_date": m.group(4),
            "notified_date": m.group(5),
            "amount_low": _to_int(m.group(6)),
            "amount_high": _to_int(m.group(7)),
        })
        prev_end = m.end()
    return rows


def parse_filer(text):
    """Pull filer name, status and district from the header."""
    flat = re.sub(r"\s+", " ", text)
    name = re.search(r"Name:\s*(.+?)\s+Status:", flat)
    status = re.search(r"Status:\s*(.+?)\s+State/District:", flat)
    dist = re.search(r"State/District:\s*([A-Z]{2}\d{2})", flat)
    return {
        "filer_name": name.group(1).strip() if name else None,
        "status": status.group(1).strip() if status else None,
        "district": dist.group(1) if dist else None,
    }
