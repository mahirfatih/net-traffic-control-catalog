"""Source-specific review policies shared by offline and live audits."""
import re


FINANCE_SIGNAL_RE = re.compile(
    r"(bank|banc|banq|banque|banka|banco|banken|banking|credit|cred|"
    r"financ|pay|pago|wallet|card|cash|loan|invest|broker|trade|"
    r"securit|capital|asset|wealth|fund|mortgage|insurance|insur|"
    r"lease|leasing|union|sparkasse|raiffeisen|volksbank|voba|"
    r"vrbank|ziraat|akbank|alfa|hsbc|ing|seb|dbs|ubs|visa|"
    r"mastercard|amex|paypal|stripe|adyen|skrill|venmo|westernunion|"
    r"alipay|klarna|revolut|wise|monzo|n26|bbva|santander|barclays|"
    r"lloyds|natwest|citi|chase|wellsfargo|fidelity|vanguard|"
    r"robinhood|3ds|3dsecure|acs)",
    re.IGNORECASE,
)


FINANCE_PAGE_RE = re.compile(
    r"\b(bank|banking|credit union|credit card|debit card|payment|payments|"
    r"financial|finance|fintech|insurance|investment|investing|brokerage|"
    r"mortgage|loan|loans|wallet|3d secure|3-d secure|visa|mastercard|"
    r"american express|swift|sepa|iban|savings|checking|wealth|asset management)\b",
    re.IGNORECASE,
)


NON_FINANCE_PAGE_RE = re.compile(
    r"\b(airline|flight|flights|hotel|booking|ticketing|cinema|streaming|"
    r"torrent|casino|adult|university|school|news|newspaper|recipe)\b",
    re.IGNORECASE,
)


SOURCE_POLICIES = {
    "adguard-https-exclusions-banks": {
        "expected_category": "finance",
        "known_false_positives": {
            "qantas.com": "airline/travel domain; not a finance service",
        },
        "weak_signal_re": FINANCE_SIGNAL_RE,
        "page_positive_re": FINANCE_PAGE_RE,
        "page_negative_re": NON_FINANCE_PAGE_RE,
    }
}
