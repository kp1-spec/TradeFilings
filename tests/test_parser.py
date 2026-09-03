import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ptr_parser import parse_ptr_text, parse_filer

MODERN = """Clerk of the House of Representatives • Legislative Resource Center • B-81 Cannon Building • Washington, DC 20515
FILER INFORMATION
Name: Hon. Jane Q. Example
Status: Member
State/District: NJ08
TRANSACTIONS
ID Owner Asset Transaction Date Notification Amount Cap.
Type Date Gains >
$200?
SP Apple Inc. - Common Stock (AAPL) [ST] P 12/22/2025 12/22/2025 $1,000,001 -
$5,000,000
SP NVIDIA Corporation - Common Stock (NVDA) [ST] S 12/22/2025 12/22/2025 $500,001 - Yes
$1,000,000
D: Sold 10,000 shares.
Microsoft Corporation (MSFT) [ST] S (partial) 01/03/2026 01/05/2026 $15,001 - $50,000
DC iShares Core S&P 500 ETF (IVV) [EF] P 01/10/2026 01/12/2026 $1,001 - $15,000
FILING STATUS: New
"""

OLD = """PERIODIC TRANSACTION REPORT
Filer Information
Name: Hon. David E. Price
Status: Member
State/District: NC04
Transactions
ID Owner Asset Transaction Type Date Notification Date Amount
Treaty Energy Corporation (TECO) s 07/1/2016 08/6/2016 $1,001 - $15,000
FILING STATUS: New
"""


def test_modern():
    rows = parse_ptr_text(MODERN)
    assert len(rows) == 4, rows
    assert rows[0]["ticker"] == "AAPL" and rows[0]["tx_type"] == "Buy"
    assert rows[0]["amount_high"] == 5000000 and rows[0]["owner"] == "Spouse"
    assert rows[1]["ticker"] == "NVDA" and rows[1]["tx_type"] == "Sell"
    assert rows[2]["asset"].startswith("Microsoft") and rows[2]["tx_type"] == "Sell (partial)"
    assert rows[3]["owner"] == "Dependent child" and rows[3]["asset_type"] == "EF"
    f = parse_filer(MODERN)
    assert f["filer_name"] == "Hon. Jane Q. Example" and f["district"] == "NJ08"


def test_old():
    rows = parse_ptr_text(OLD)
    assert len(rows) == 1
    assert rows[0]["ticker"] == "TECO" and rows[0]["tx_type"] == "Sell"
    assert rows[0]["asset"] == "Treaty Energy Corporation"


if __name__ == "__main__":
    test_modern(); test_old()
    for r in parse_ptr_text(MODERN):
        print(r)
    print("all tests passed")
