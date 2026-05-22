"""
Amazon Affiliate Helper — No PA API required.
Uses your Associate Tag directly in hardcoded product URLs.
All links earn full commission. Zero API calls.

Required in .env:
    AMAZON_ASSOCIATE_TAG  e.g. aitoolsidea-21
    AMAZON_REGION         'in' (default) or 'us'
"""

import os
from pathlib import Path

def load_dotenv():
    for p in [Path(".env"), Path(__file__).parent.parent / ".env"]:
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            return

load_dotenv()

ASSOCIATE_TAG = os.environ.get("AMAZON_ASSOCIATE_TAG", "")
REGION        = os.environ.get("AMAZON_REGION", "in")

DOMAIN = {
    "in": "www.amazon.in",
    "us": "www.amazon.com",
    "uk": "www.amazon.co.uk",
}.get(REGION, "www.amazon.in")

def _url(asin: str) -> str:
    if ASSOCIATE_TAG:
        return f"https://{DOMAIN}/dp/{asin}?tag={ASSOCIATE_TAG}"
    return f"https://{DOMAIN}/dp/{asin}"

# ── Curated product catalogue ─────────────────────────────────────────────────
# ASINs verified on amazon.in. Add more as you find good converters.
# Structure: topic_key → list of products (best first)
CATALOGUE = {
    "productivity": [
        {"asin": "0735211299", "title": "Atomic Habits — James Clear",             "price": "₹399",   "cat": "Book"},
        {"asin": "B08N5LNQCX", "title": "Logitech MX Keys Wireless Keyboard",      "price": "₹8,995", "cat": "Office Gear"},
        {"asin": "B07PDHSJ1J", "title": "Anker USB-C Hub 7-in-1",                  "price": "₹2,999", "cat": "Office Gear"},
    ],
    "automation": [
        {"asin": "0735211299", "title": "Atomic Habits — James Clear",              "price": "₹399",   "cat": "Book"},
        {"asin": "B07YWMFLHK", "title": "Deep Work — Cal Newport",                 "price": "₹349",   "cat": "Book"},
        {"asin": "B07PDHSJ1J", "title": "Anker USB-C Hub 7-in-1",                  "price": "₹2,999", "cat": "Office Gear"},
    ],
    "writing": [
        {"asin": "0385490259", "title": "On Writing — Stephen King",                "price": "₹499",   "cat": "Book"},
        {"asin": "0735211299", "title": "Atomic Habits — James Clear",              "price": "₹399",   "cat": "Book"},
        {"asin": "B087Z17VHV", "title": "Blue Yeti USB Microphone",                 "price": "₹9,999", "cat": "Microphone"},
    ],
    "freelance": [
        {"asin": "0887307280", "title": "The E-Myth Revisited — Michael Gerber",   "price": "₹499",   "cat": "Book"},
        {"asin": "0385490259", "title": "On Writing — Stephen King",                "price": "₹499",   "cat": "Book"},
        {"asin": "B07PDHSJ1J", "title": "Anker USB-C Hub 7-in-1",                  "price": "₹2,999", "cat": "Office Gear"},
    ],
    "home office": [
        {"asin": "B08N5LNQCX", "title": "Logitech MX Keys Wireless Keyboard",      "price": "₹8,995", "cat": "Office Gear"},
        {"asin": "B07TLKDZNY", "title": "Logitech MX Master 3 Wireless Mouse",     "price": "₹6,495", "cat": "Office Gear"},
        {"asin": "B087Z17VHV", "title": "Blue Yeti USB Microphone",                 "price": "₹9,999", "cat": "Microphone"},
        {"asin": "B07PDHSJ1J", "title": "Anker USB-C Hub 7-in-1",                  "price": "₹2,999", "cat": "Office Gear"},
    ],
    "remote work": [
        {"asin": "B08N5LNQCX", "title": "Logitech MX Keys Wireless Keyboard",      "price": "₹8,995", "cat": "Office Gear"},
        {"asin": "B08G5K5362", "title": "Anker PowerConf S3 Speakerphone",          "price": "₹7,999", "cat": "Office Gear"},
        {"asin": "B087Z17VHV", "title": "Blue Yeti USB Microphone",                 "price": "₹9,999", "cat": "Microphone"},
    ],
    "crm": [
        {"asin": "0887307280", "title": "The E-Myth Revisited — Michael Gerber",   "price": "₹499",   "cat": "Book"},
        {"asin": "0735211299", "title": "Atomic Habits — James Clear",              "price": "₹399",   "cat": "Book"},
    ],
    "email": [
        {"asin": "0735211299", "title": "Atomic Habits — James Clear",              "price": "₹399",   "cat": "Book"},
        {"asin": "0887307280", "title": "The E-Myth Revisited — Michael Gerber",   "price": "₹499",   "cat": "Book"},
    ],
    "scheduling": [
        {"asin": "B07YWMFLHK", "title": "Deep Work — Cal Newport",                 "price": "₹349",   "cat": "Book"},
        {"asin": "0735211299", "title": "Atomic Habits — James Clear",              "price": "₹399",   "cat": "Book"},
    ],
    "project": [
        {"asin": "B07YWMFLHK", "title": "Deep Work — Cal Newport",                 "price": "₹349",   "cat": "Book"},
        {"asin": "B08N5LNQCX", "title": "Logitech MX Keys Wireless Keyboard",      "price": "₹8,995", "cat": "Office Gear"},
    ],
    "ai tools": [
        {"asin": "1250294177", "title": "AI Superpowers — Kai-Fu Lee",              "price": "₹499",   "cat": "Book"},
        {"asin": "0735211299", "title": "Atomic Habits — James Clear",              "price": "₹399",   "cat": "Book"},
        {"asin": "B08N5LNQCX", "title": "Logitech MX Keys Wireless Keyboard",      "price": "₹8,995", "cat": "Office Gear"},
    ],
    "headphone": [
        {"asin": "B0CCK3SXKK", "title": "Sony WH-1000XM5 Noise Cancelling Headphones","price": "₹24,990","cat": "Headphones"},
        {"asin": "B08N5LNQCX", "title": "Logitech MX Keys Wireless Keyboard",      "price": "₹8,995", "cat": "Office Gear"},
    ],
    "webcam": [
        {"asin": "B07K95WFWM", "title": "Logitech C920 HD Pro Webcam",             "price": "₹7,495", "cat": "Webcam"},
        {"asin": "B087Z17VHV", "title": "Blue Yeti USB Microphone",                 "price": "₹9,999", "cat": "Microphone"},
    ],
    "microphone": [
        {"asin": "B087Z17VHV", "title": "Blue Yeti USB Microphone",                 "price": "₹9,999", "cat": "Microphone"},
        {"asin": "B08G5K5362", "title": "Anker PowerConf S3 Speakerphone",          "price": "₹7,999", "cat": "Office Gear"},
    ],
    "book": [
        {"asin": "0735211299", "title": "Atomic Habits — James Clear",              "price": "₹399",   "cat": "Book"},
        {"asin": "0887307280", "title": "The E-Myth Revisited — Michael Gerber",   "price": "₹499",   "cat": "Book"},
        {"asin": "B07YWMFLHK", "title": "Deep Work — Cal Newport",                 "price": "₹349",   "cat": "Book"},
        {"asin": "1250294177", "title": "AI Superpowers — Kai-Fu Lee",              "price": "₹499",   "cat": "Book"},
    ],
    "default": [
        {"asin": "0735211299", "title": "Atomic Habits — James Clear",              "price": "₹399",   "cat": "Book"},
        {"asin": "B07YWMFLHK", "title": "Deep Work — Cal Newport",                 "price": "₹349",   "cat": "Book"},
        {"asin": "B07PDHSJ1J", "title": "Anker USB-C Hub 7-in-1",                  "price": "₹2,999", "cat": "Office Gear"},
    ],
}

# ── Public functions ──────────────────────────────────────────────────────────

def get_amazon_products(keyword: str, count: int = 3) -> list[dict]:
    """
    Returns up to `count` products relevant to the keyword.
    Each dict: {asin, title, price, cat, url}
    No API call. Uses ASSOCIATE_TAG in URL directly.
    """
    kw = keyword.lower()
    matched = []
    for key, products in CATALOGUE.items():
        if key != "default" and key in kw:
            matched.extend(products)
    if not matched:
        matched = CATALOGUE["default"]

    # De-duplicate by ASIN
    seen, result = set(), []
    for p in matched:
        if p["asin"] not in seen:
            seen.add(p["asin"])
            result.append({**p, "url": _url(p["asin"])})
        if len(result) >= count:
            break

    tag_status = f"tag={ASSOCIATE_TAG}" if ASSOCIATE_TAG else "NO TAG SET"
    print(f"      [Amazon] {len(result)} products ({tag_status})")
    return result


def products_to_markdown(products: list[dict]) -> str:
    """Markdown block injected into each article — renders as a table."""
    if not products:
        return ""
    lines = [
        "\n---\n",
        "### 📦 Useful Tools & Books on Amazon\n",
        "> *These are affiliate links — you pay the same price, "
        "we earn a small commission that keeps this site running.*\n",
        "| Product | Category | Price | Link |",
        "|---------|----------|-------|------|",
    ]
    for p in products:
        title = p["title"][:52] + ("…" if len(p["title"]) > 52 else "")
        lines.append(f"| **{title}** | {p['cat']} | {p['price']} | [View →]({p['url']}) |")
    lines.append("\n")
    return "\n".join(lines)


def build_amazon_frontmatter_yaml(products: list[dict]) -> str:
    """Converts product list to YAML array for frontmatter injection."""
    if not products:
        return "amazonProducts: []"
    lines = ["amazonProducts:"]
    for p in products:
        title = p["title"].replace('"', "'")
        lines.append(f'  - title: "{title}"')
        lines.append(f'    price: "{p["price"]}"')
        lines.append(f'    url: "{p["url"]}"')
        lines.append(f'    cat: "{p.get("cat", "Amazon")}"')
    return "\n".join(lines)