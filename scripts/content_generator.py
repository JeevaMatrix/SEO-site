"""
Content Generator — FREE Programmatic SEO + Dual Affiliate System
Groq (free) for generation. Amazon Associates (tag links) + SaaS affiliates for max cashflow.

FREE APIs:
  Groq:   console.groq.com    → 14,400 req/day FREE
  Gemini: aistudio.google.com → 1,500 req/day FREE (optional QA)

Required env vars (.env):
    GROQ_API_KEY
    SUPABASE_URL
    SUPABASE_KEY
    AMAZON_ASSOCIATE_TAG    ← e.g. aitoolsidea-21
    AMAZON_REGION           ← 'in' for India (default), 'us' for USA
    UNSPLASH_KEY            (optional)
    GEMINI_API_KEY          (optional QA)
    ARTICLES_PER_RUN        (default 5)
"""

import os, json, re, subprocess, sys
from datetime import datetime
from pathlib import Path

def install(pkg):
    subprocess.run([sys.executable, "-m", "pip", "install", pkg, "-q"], check=True)

try:
    import requests
except ImportError:
    install("requests"); import requests
try:
    from supabase import create_client
except ImportError:
    install("supabase"); from supabase import create_client

# ── Load .env ─────────────────────────────────────────────────────────────────
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

# ── Config ────────────────────────────────────────────────────────────────────
GROQ_KEY         = os.environ.get("GROQ_API_KEY", "")
GEMINI_KEY       = os.environ.get("GEMINI_API_KEY", "")
SUPABASE_URL     = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY     = os.environ.get("SUPABASE_KEY", "")
UNSPLASH_KEY     = os.environ.get("UNSPLASH_KEY", "")
ARTICLES_PER_RUN = int(os.environ.get("ARTICLES_PER_RUN", "5"))
CONTENT_DIR      = Path("src/content/blog")
YEAR             = datetime.now().year

missing = [v for v in ["GROQ_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"] if not os.environ.get(v)]
if missing:
    print(f"ERROR: Missing env vars: {', '.join(missing)}")
    sys.exit(1)

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── Import Amazon helper ───────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
try:
    from amazon_helper import get_amazon_products, products_to_markdown, build_amazon_frontmatter_yaml
    AMAZON_ENABLED = bool(os.environ.get("AMAZON_ASSOCIATE_TAG"))
except ImportError:
    def get_amazon_products(kw, count=3): return []
    def products_to_markdown(p): return ""
    def build_amazon_frontmatter_yaml(p): return "amazonProducts: []"
    AMAZON_ENABLED = False

# ── SaaS Affiliate Programs ───────────────────────────────────────────────────
# Replace YOURCODE with your actual ref code per tool.
# Apply directly at each tool's affiliate page (all instant/1-day approval):
#   Zapier:  zapier.com/affiliate
#   Notion:  notion.so/affiliates
#   ClickUp: clickup.com/affiliates
#   Make:    make.com/en/affiliate
#   HubSpot: hubspot.com/partners/affiliates
SAAS_AFFILIATES = {
    "zapier":    {"url": "https://zapier.com?via=YOURCODE",               "name": "Zapier",    "commission": "20-30% recurring"},
    "notion":    {"url": "https://notion.so/affiliates/YOURCODE",         "name": "Notion",    "commission": "$10/signup"},
    "clickup":   {"url": "https://clickup.com?fp_ref=YOURCODE",           "name": "ClickUp",   "commission": "20% recurring"},
    "make":      {"url": "https://www.make.com/en/register?pc=YOURCODE",  "name": "Make.com",  "commission": "20% recurring"},
    "monday":    {"url": "https://monday.com/?r=YOURCODE",                "name": "Monday.com","commission": "$25-$100/sale"},
    "calendly":  {"url": "https://calendly.com/pages/pricing?ref=YOURCODE","name": "Calendly", "commission": "$10-30/sale"},
    "hubspot":   {"url": "https://hubspot.com/?hubs_signup-url=YOURCODE", "name": "HubSpot",  "commission": "30% recurring"},
    "airtable":  {"url": "https://airtable.com/invite/r/YOURCODE",        "name": "Airtable", "commission": "$10/signup"},
    "pipedrive": {"url": "https://www.pipedrive.com/en/invite/YOURCODE",  "name": "Pipedrive","commission": "20% recurring"},
    "grammarly": {"url": "https://www.grammarly.com/referrals/YOURCODE",  "name": "Grammarly","commission": "$0.20 free / $20 paid"},
}

def get_saas_aff(product: str, keyword: str = "") -> dict | None:
    """
    Returns SaaS affiliate entry by checking affiliate_product column first,
    then falling back to scanning the keyword itself.
    e.g. keyword "zapier vs pabbly" → matches zapier even if affiliate_product is empty.
    """
    for search_str in [(product or "").lower(), (keyword or "").lower()]:
        if not search_str:
            continue
        for k, v in SAAS_AFFILIATES.items():
            if k in search_str:
                return v
    return None

# ── Keyword → Amazon product search query mapping ─────────────────────────────
# Tells get_amazon_products() what to search for, per article topic.
AMAZON_KEYWORD_MAP = {
    "productivity":  "productivity books for entrepreneurs",
    "automation":    "business automation book",
    "writing":       "AI writing business books",
    "freelance":     "freelancing business books",
    "home office":   "home office setup accessories",
    "remote work":   "remote work home office gear",
    "crm":           "small business crm books sales",
    "email":         "email marketing books business",
    "scheduling":    "time management productivity books",
    "project":       "project management books business",
    "book":          "best business books 2024",
    "gear":          "home office accessories productivity",
    "headphone":     "noise cancelling headphones work from home",
    "webcam":        "webcam for remote work meetings",
    "microphone":    "USB microphone podcast recording",
    "keyboard":      "wireless keyboard productivity",
    "default":       "business productivity books",
}

def get_amazon_query(keyword: str) -> str:
    kw = keyword.lower()
    for key, query in AMAZON_KEYWORD_MAP.items():
        if key != "default" and key in kw:
            return query
    return AMAZON_KEYWORD_MAP["default"]

# ── Groq API ──────────────────────────────────────────────────────────────────
def groq(prompt, max_tokens=3500, retries=3):
    """Call Groq API with retry logic for connection drops (common on free tier)."""
    import time
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile",
                      "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": max_tokens, "temperature": 0.7},
                timeout=120,   # bumped from 90 — large prompts need more time
            )
            if r.status_code == 429:
                wait = int(r.headers.get("retry-after", 10))
                print(f"      [Groq] Rate limited — waiting {wait}s...")
                time.sleep(wait)
                continue
            if r.status_code != 200:
                raise Exception(f"Groq {r.status_code}: {r.text[:200]}")
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            last_err = e
            if attempt < retries:
                wait = attempt * 5   # 5s, 10s between retries
                print(f"      [Groq] Attempt {attempt} failed ({e}) — retrying in {wait}s...")
                time.sleep(wait)
    raise Exception(f"Groq failed after {retries} attempts: {last_err}")

# ── Gemini API (optional QA) ──────────────────────────────────────────────────
def gemini(prompt, max_tokens=100):
    if not GEMINI_KEY: return ""
    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}",
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.1}},
            timeout=20,
        )
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return ""

# ── Prompt builder ────────────────────────────────────────────────────────────
TYPE_GUIDE = {
    "comparison":  "Include a markdown comparison table (min 5 data points: price, features, ease, best for, support). End with clear winner per use case.",
    "review":      "Include pricing table (all plan tiers). List 3+ specific pros AND 3+ specific cons. Add 'Who should avoid this' section.",
    "listicle":    "Start with a quick comparison table. Each item as H3 with: price, best for, one key limitation.",
    "how-to":      "Use numbered steps. Describe what user sees after each step. Add troubleshooting section. State time required.",
    "alternatives":"Compare vs the original tool in a table. Explain why someone switches. Separate free vs paid options.",
}

def make_prompt(keyword: str, article_type: str, saas_aff: dict | None) -> str:
    guide = TYPE_GUIDE.get(article_type, TYPE_GUIDE["review"])
    year  = YEAR

    if saas_aff:
        aff_instruction = f"""FEATURED SAAS TOOL: {saas_aff['name']}
SAAS AFFILIATE LINK (insert 2-3 times naturally as markdown links): {saas_aff['url']}
Example insertion: [Try {saas_aff['name']} free]({saas_aff['url']})"""
        aff_name = saas_aff["name"]
    else:
        aff_instruction = "No specific tool to feature. Focus on comparison / general advice. Be tool-agnostic and helpful."
        aff_name = "various tools"

    saas_url = saas_aff["url"] if saas_aff else "#"

    return f"""You are a senior tech writer for a site helping small business owners choose AI and automation tools.

TARGET KEYWORD: "{keyword}"
ARTICLE TYPE: {article_type}
YEAR: {year}
{aff_instruction}

FORMAT REQUIREMENT: {guide}

WRITING RULES:
- Sentence 1 must name the reader's exact problem
- Write for non-technical SMB owners — practical, specific, brutally honest
- Include real pricing (use your knowledge, note "as of {year}")
- 2-3 "Pro tip:" callouts with genuinely useful, non-obvious advice
- NEVER use: delve, leverage, utilize, embark, game-changer, straightforward, certainly, absolutely, in conclusion, it's worth noting
- Length: 1600-2200 words. This is critical — articles under 1200 words will be rejected.
- End with a '## Frequently Asked Questions' section with 4 H3 questions + paragraph answers
- Leave a placeholder line exactly as: <!--AMAZON_PRODUCTS_HERE--> near the end before FAQs (the system will auto-inject Amazon product recommendations here)

RETURN: Only valid Markdown starting with this exact frontmatter:

---
title: "{keyword} — Complete Guide [{year}]"
description: "WRITE REAL META DESC: 130-155 chars, include keyword"
pubDate: {datetime.now().strftime('%Y-%m-%d')}
updatedDate: {datetime.now().strftime('%Y-%m-%d')}
tags: ["ai tools", "small business", "productivity"]
image: "PLACEHOLDER_IMAGE"
affiliate: "{aff_name}"
affiliateUrl: "{saas_url}"
---

[article body — write the full article here, minimum 1600 words]

<!--AMAZON_PRODUCTS_HERE-->

## Frequently Asked Questions

Write 4 real FAQ entries as H3 + paragraph pairs that people actually search for about this topic.
Format each as:
### Question here?
Answer here (2-4 sentences).
"""

# ── QA ────────────────────────────────────────────────────────────────────────
BAD_PHRASES = ["delve", "it's worth noting", "certainly!", "absolutely!", "game-changer",
               "straightforward", "embark on", "in conclusion,", "leveraging", "utilize"]

def qa(content: str, keyword: str) -> tuple[int, list[str]]:
    score, issues = 100, []
    kw, cl = keyword.lower(), content.lower()
    words  = content.split()

    if kw not in cl[:600]:         score -= 15; issues.append("Keyword missing from intro")
    if len(words) < 900:           score -= 20; issues.append(f"Too short ({len(words)} words)")
    elif len(words) < 1200:        score -= 8;  issues.append(f"Short ({len(words)} words)")
    if content.count("\n## ") < 2: score -= 10; issues.append("Need 2+ H2 headings")
    if "faq" not in cl:            score -= 10; issues.append("Missing FAQ section")
    if "| " not in content:        score -= 5;  issues.append("Missing markdown table")
    if "---\n" not in content[:300]: score -= 10; issues.append("Missing frontmatter")

    bad = [p for p in BAD_PHRASES if p in cl]
    if bad: score -= min(len(bad)*4, 20); issues.append(f"AI phrases: {bad[:2]}")

    bonus = 0
    if GEMINI_KEY:
        try:
            result = gemini(
                f'Rate 0-20: is this article genuinely useful (not generic AI fluff) '
                f'for a small business owner? Keyword: "{keyword}". '
                f'Article start: {content[300:1200]}\nReply ONLY with a number.', 10)
            bonus = min(int(re.search(r"\d+", result).group()), 20)
        except Exception:
            bonus = 10
    else:
        bonus = 10

    return min(100, score + bonus), issues

# ── Images ─────────────────────────────────────────────────────────────────
# Priority order:
# 1. Unsplash API (if key approved — set UNSPLASH_KEY)
# 2. Pexels API  (free, instant approval — set PEXELS_KEY at pexels.com/api)
# 3. Picsum Photos (no key, random high-quality — always works)
# 4. Curated topic-matched Unsplash direct URLs (no API, always works)

PEXELS_KEY = os.environ.get("PEXELS_KEY", "")

# ── Topic → visual search query mapping ──────────────────────────────────────
# NEVER search the article keyword directly ("zapier vs n8n" = 0 results).
# Instead map to a generic visual concept that always has stock photos.
TOPIC_SEARCH_QUERIES = {
    "zapier":        "workflow automation dashboard",
    "n8n":           "workflow automation dashboard",
    "make":          "workflow automation dashboard",
    "pabbly":        "workflow automation dashboard",
    "automation":    "workflow automation dashboard",
    "notion":        "productivity workspace desk",
    "clickup":       "project management team",
    "airtable":      "spreadsheet database workspace",
    "monday":        "team collaboration office",
    "asana":         "project management team",
    "crm":           "sales team office meeting",
    "hubspot":       "sales team office meeting",
    "pipedrive":     "sales team office meeting",
    "salesforce":    "sales team office meeting",
    "email":         "email marketing laptop",
    "mailchimp":     "email marketing laptop",
    "brevo":         "email marketing laptop",
    "writing":       "person writing laptop coffee",
    "copy":          "person writing laptop coffee",
    "content":       "person writing laptop coffee",
    "chatgpt":       "artificial intelligence technology",
    "ai":            "artificial intelligence technology",
    "gpt":           "artificial intelligence technology",
    "freelance":     "freelancer working laptop home",
    "solopreneur":   "freelancer working laptop home",
    "scheduling":    "calendar planning desk",
    "calendly":      "calendar planning desk",
    "booking":       "calendar planning desk",
    "project":       "project management team whiteboard",
    "marketing":     "digital marketing analytics chart",
    "seo":           "seo analytics laptop chart",
    "social media":  "social media phone laptop",
    "sales":         "sales team meeting handshake",
    "productivity":  "productive person desk focus",
    "remote":        "remote work home office setup",
    "startup":       "startup team office brainstorm",
    "small business":"small business owner laptop",
    "ecommerce":     "ecommerce online shopping laptop",
    "invoice":       "business finance accounting",
    "payment":       "business finance accounting",
    "customer":      "customer service support",
    "chatbot":       "artificial intelligence chat",
    "data":          "data analytics dashboard charts",
    "spreadsheet":   "spreadsheet data analysis laptop",
    "default":       "productive business workspace laptop",
}

# Hardcoded curated URLs as final fallback — verified working, no API needed
# One unique image per category so articles don't all look the same
CURATED_FALLBACKS = {
    "workflow automation dashboard":        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&q=80",
    "productivity workspace desk":          "https://images.unsplash.com/photo-1484480974693-6ca0a78fb36b?w=1200&q=80",
    "project management team":              "https://images.unsplash.com/photo-1611224923853-80b023f02d71?w=1200&q=80",
    "sales team office meeting":            "https://images.unsplash.com/photo-1552664730-d307ca884978?w=1200&q=80",
    "email marketing laptop":               "https://images.unsplash.com/photo-1596526131083-e8c633c948d2?w=1200&q=80",
    "person writing laptop coffee":         "https://images.unsplash.com/photo-1455390582262-044cdead277a?w=1200&q=80",
    "artificial intelligence technology":   "https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=1200&q=80",
    "freelancer working laptop home":       "https://images.unsplash.com/photo-1499750310107-5fef28a66643?w=1200&q=80",
    "calendar planning desk":               "https://images.unsplash.com/photo-1506784983877-45594efa4cbe?w=1200&q=80",
    "digital marketing analytics chart":    "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1200&q=80",
    "productive person desk focus":         "https://images.unsplash.com/photo-1484480974693-6ca0a78fb36b?w=1200&q=80",
    "remote work home office setup":        "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=1200&q=80",
    "small business owner laptop":          "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=1200&q=80",
    "data analytics dashboard charts":      "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&q=80",
    "productive business workspace laptop": "https://images.unsplash.com/photo-1551434678-e076c223a692?w=1200&q=80",
}

def _get_visual_query(topic: str) -> str:
    """Map article topic/keyword to a generic visual search query with real results."""
    t = topic.lower()
    for key, query in TOPIC_SEARCH_QUERIES.items():
        if key != "default" and key in t:
            return query
    return TOPIC_SEARCH_QUERIES["default"]

def _curated_fallback(visual_query: str) -> str:
    """Return a curated image URL for a visual query. Deterministic — same query = same image."""
    if visual_query in CURATED_FALLBACKS:
        return CURATED_FALLBACKS[visual_query]
    # Picsum with seed from query hash — consistent per topic
    seed = abs(hash(visual_query)) % 1000
    return f"https://picsum.photos/seed/{seed}/1200/630"

def get_image(topic: str) -> str:
    """
    Returns a relevant image URL for the article topic.

    Pipeline:
      1. Unsplash API  — searches a generic visual query (NOT the keyword)
      2. Pexels API    — same approach, instant free approval at pexels.com/api
      3. Curated map   — hardcoded verified URLs by visual category, no API
      4. Picsum        — deterministic random photo, always works, no API

    NEVER searches the raw keyword — "zapier vs n8n" → "workflow automation dashboard"
    """
    visual_query = _get_visual_query(topic)

    # 1. Unsplash API
    if UNSPLASH_KEY:
        try:
            r = requests.get(
                "https://api.unsplash.com/search/photos",
                params={"query": visual_query, "per_page": 3, "orientation": "landscape"},
                headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"},
                timeout=10,
            )
            results = r.json().get("results", [])
            if results:
                # Pick deterministically by topic hash so same topic = same image
                idx = abs(hash(topic)) % len(results)
                return results[idx]["urls"]["regular"]
        except Exception:
            pass

    # 2. Pexels API
    if PEXELS_KEY:
        try:
            r = requests.get(
                "https://api.pexels.com/v1/search",
                params={"query": visual_query, "per_page": 3, "orientation": "landscape"},
                headers={"Authorization": PEXELS_KEY},
                timeout=10,
            )
            photos = r.json().get("photos", [])
            if photos:
                idx = abs(hash(topic)) % len(photos)
                return photos[idx]["src"]["large2x"]
        except Exception:
            pass

    # 3. Curated verified fallback
    return _curated_fallback(visual_query)

# ── Helpers ───────────────────────────────────────────────────────────────────
def slugify(t: str) -> str:
    t = t.lower().strip()
    t = re.sub(r"[^\w\s-]", "", t)
    t = re.sub(r"[\s_-]+", "-", t)
    return t[:80].strip("-")


def truncate_title(content: str) -> str:
    """
    Safely truncate the title value in YAML frontmatter to max 110 chars.
    Handles both quoted and unquoted title values.
    Preserves surrounding frontmatter exactly.
    """
    import re

    # Match: title: "some value" or title: some value (with or without quotes)
    pattern = re.compile(
        r'^(title:\s*)(["\']?)(.+?)\2(\s*)$',
        re.MULTILINE
    )

    def shorten(m):
        prefix  = m.group(1)   # "title: "
        quote   = m.group(2)   # " or ' or empty
        value   = m.group(3)   # the actual title text
        suffix  = m.group(4)   # trailing whitespace

        if len(value) > 110:
            value = value[:107].rsplit(" ", 1)[0].rstrip(" :-—") + "..."

        # Always write with double quotes for YAML safety
        # Escape any double quotes inside the value
        value = value.replace('"', "\\'")
        return f'title: "{value}"{suffix}'

    return pattern.sub(shorten, content, count=1)


def save(slug: str, content: str, image_url: str, amazon_products: list[dict]):
    """
    Write article to disk. Bulletproof approach:
    1. Split content into frontmatter + body using regex (no index tricks)
    2. Parse frontmatter line by line, inject amazon fields cleanly
    3. Rejoin and write
    """
    import re as _re

    CONTENT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Step 1: split frontmatter from body ──────────────────────────────
    # Match opening ---, frontmatter lines, closing --- on its own line
    fm_match = _re.match(r'^---\r?\n(.*?)\n---\r?\n(.*)', content, _re.DOTALL)
    if not fm_match:
        # No valid frontmatter found — write as-is with image replaced
        content = content.replace("PLACEHOLDER_IMAGE", image_url)
        (CONTENT_DIR / f"{slug}.md").write_text(content, encoding="utf-8")
        print(f"      [save] Warning: no frontmatter found in {slug}.md")
        return

    fm_raw  = fm_match.group(1)   # frontmatter text (between --- markers)
    body    = fm_match.group(2)   # everything after closing ---

    # ── Step 2: inject image into frontmatter ─────────────────────────────
    fm_raw = fm_raw.replace("PLACEHOLDER_IMAGE", image_url)
    body   = body.replace("PLACEHOLDER_IMAGE", image_url)  # fallback

    # ── Step 3: truncate title safely ─────────────────────────────────────
    def fix_title_line(line):
        m = _re.match(r'title:\s*["\']?(.+?)["\']?\s*$', line)
        if not m: return line
        val = m.group(1).strip().strip('"').strip("'")
        if len(val) > 105:
            val = val[:102].rsplit(" ", 1)[0].rstrip(" :-—") + "..."
        val = val.replace('"',"'")  # no double quotes inside double-quoted string
        return f'title: "{val}"'

    fm_lines = fm_raw.splitlines()
    fm_lines = [fix_title_line(l) if l.startswith("title:") else l for l in fm_lines]

    # ── Step 4: remove any stale amazonProducts lines (from previous run) ──
    clean_lines, skip = [], False
    for line in fm_lines:
        if line.startswith("amazonProducts:"):
            skip = True; continue
        if skip and (line.startswith("  -") or line.startswith("    ")):
            continue
        skip = False
        # Also strip any YAML comment lines (# ...) — they confuse gray-matter
        if line.strip().startswith("#"):
            continue
        clean_lines.append(line)
    fm_lines = clean_lines

    # ── Step 5: build amazonProducts YAML lines ───────────────────────────
    if amazon_products:
        am_lines = ["amazonProducts:"]
        for p in amazon_products:
            def ys(v):  # yaml-safe: escape double quotes, no newlines
                return str(v).replace("\\","\\\\").replace('"',"'").replace("\n"," ")
            am_lines.append(f'  - title: "{ys(p.get("title","Product"))}"')
            am_lines.append(f'    price: "{ys(p.get("price",""))}"')
            am_lines.append(f'    url:   "{ys(p.get("url","#"))}"')
            am_lines.append(f'    cat:   "{ys(p.get("cat","Amazon"))}"')
        fm_lines.extend(am_lines)
    else:
        fm_lines.append("amazonProducts: []")

    # ── Step 6: inject amazon table into body ─────────────────────────────
    amazon_md = products_to_markdown(amazon_products)
    if "<!--AMAZON_PRODUCTS_HERE-->" in body and amazon_md:
        body = body.replace("<!--AMAZON_PRODUCTS_HERE-->", amazon_md)
    elif amazon_md and "## Frequently Asked Questions" in body:
        body = body.replace(
            "## Frequently Asked Questions",
            amazon_md + "\n\n## Frequently Asked Questions"
        )
    elif amazon_md:
        body = body + "\n\n" + amazon_md

    # ── Step 7: reassemble and write ─────────────────────────────────────
    final = "---\n" + "\n".join(fm_lines) + "\n---\n" + body
    (CONTENT_DIR / f"{slug}.md").write_text(final, encoding="utf-8")


def git_push(count: int):
    try:
        subprocess.run(["git", "add", str(CONTENT_DIR)], check=True)
        diff = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
        if diff.returncode != 0:
            subprocess.run(["git", "commit", "-m",
                f"content: add {count} articles [{datetime.now().strftime('%Y-%m-%d')}] [bot]"],
                check=True)
            subprocess.run(["git", "push"], check=True)
            print(f"\n✓ Pushed → Vercel deploys in ~30s")
    except subprocess.CalledProcessError as e:
        print(f"Git note: {e}")

# ── Main ──────────────────────────────────────────────────────────────────────
def run():
    amazon_tag = os.environ.get("AMAZON_ASSOCIATE_TAG", "NOT SET — add to .env")
    print(f"\n{'='*60}")
    print(f" Content Generator  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f" LLM: Groq llama-3.3-70b (FREE)  |  Target: {ARTICLES_PER_RUN} articles")
    print(f" Amazon tag: {amazon_tag}  |  SaaS affiliates: {len(SAAS_AFFILIATES)} programs")
    print(f"{'='*60}\n")

    rows = (sb.table("keywords").select("*").eq("status", "pending")
              .order("created_at").limit(ARTICLES_PER_RUN).execute().data)

    if not rows:
        print("No pending keywords. Run: python scripts/keyword_research.py")
        return

    generated = 0
    for i, row in enumerate(rows):
        keyword      = row["keyword"]
        article_type = row.get("article_type", "review")
        affiliate    = row.get("affiliate_product", "")

        print(f"[{i+1}/{len(rows)}] {keyword}")

        # Resolve SaaS affiliate (None if no match — Amazon-only article)
        saas_aff = get_saas_aff(affiliate, keyword)
        if saas_aff:
            print(f"      SaaS affiliate: {saas_aff['name']} ({saas_aff['commission']})")
        else:
            print(f"      SaaS affiliate: none matched — Amazon-primary article")

        try:
            # Generate article
            content = groq(make_prompt(keyword, article_type, saas_aff), max_tokens=4000)

            # QA check
            score, issues = qa(content, keyword)
            status_str = f"QA {score}/100"
            if issues: status_str += f" ({issues[0]})"
            print(f"      {status_str} — {len(content.split())} words")

            if score >= 58:
                slug = slugify(keyword)

                # Fetch Amazon products (always — even on SaaS articles for extra revenue)
                amazon_query    = get_amazon_query(keyword)
                amazon_products = get_amazon_products(amazon_query, count=3)

                image_url = get_image(affiliate or keyword.split()[0])
                save(slug, content, image_url, amazon_products)

                sb.table("keywords").update({"status": "published"}).eq("id", row["id"]).execute()
                sb.table("articles").insert({
                    "keyword_id":  row["id"],
                    "slug":        slug,
                    "title":       keyword,
                    "qa_score":    score,
                    "status":      "published",
                    "published_at": datetime.now().isoformat(),
                }).execute()
                generated += 1

                revenue_sources = []
                if saas_aff:    revenue_sources.append(f"SaaS({saas_aff['name']})")
                if amazon_products: revenue_sources.append(f"Amazon({len(amazon_products)} products)")
                print(f"      ✓ {slug}.md  |  Revenue: {' + '.join(revenue_sources) or 'none yet'}")
            else:
                print(f"      ✗ Failed QA — {issues}")
                sb.table("keywords").update({"status": "qa_failed"}).eq("id", row["id"]).execute()

        except Exception as e:
            print(f"      ✗ Error: {e}")
            sb.table("keywords").update({"status": "error"}).eq("id", row["id"]).execute()
        print()

    if generated > 0:
        git_push(generated)
    print(f"Done: {generated}/{len(rows)} published  |  API cost: $0.00")

if __name__ == "__main__":
    run()