"""
keyword_research.py — US-focused, trend-aware, income/business angle
Uses: Groq (free) + Serper (Google US) + Google Trends RSS (free, no key)
"""

import os, json, sys, subprocess, time, re
from datetime import datetime
from pathlib import Path

def install(pkg):
    subprocess.run([sys.executable,"-m","pip","install",pkg,"-q"],check=True)

try: import requests
except ImportError: install("requests"); import requests
try: from supabase import create_client
except ImportError: install("supabase"); from supabase import create_client

def load_dotenv():
    for p in [Path(".env"), Path(__file__).parent.parent/".env"]:
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k,_,v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            return

load_dotenv()

GROQ_KEY     = os.environ.get("GROQ_API_KEY","")
SERPER_KEY   = os.environ.get("SERPER_API_KEY","")
SUPABASE_URL = os.environ.get("SUPABASE_URL","")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY","")
YEAR         = datetime.now().year

print("\n=== DIAGNOSTIC ===")
print(f"GROQ_API_KEY   : {'SET ✓' if GROQ_KEY else 'MISSING ✗'}")
print(f"SERPER_API_KEY : {'SET ✓' if SERPER_KEY else 'MISSING (optional)'}")
print(f"SUPABASE_URL   : {'SET ✓' if SUPABASE_URL else 'MISSING ✗'}")

if not GROQ_KEY or not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: missing required env vars"); sys.exit(1)

print("\n=== SUPABASE ===")
try:
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    sb.table("keywords").select("id").limit(1).execute()
    print("  Tables OK ✓")
except Exception as e:
    print(f"  ERROR: {e}"); sys.exit(1)

# ── Google Trends RSS — free, no API key ─────────────────────────────────────
def get_trending_topics():
    """
    Pulls today's trending searches from Google Trends RSS feed.
    Free, no key, no quota. Returns list of trending terms.
    """
    trending = []
    urls = [
        "https://trends.google.com/trending/rss?geo=US",       # US trending
        "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US",
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=10,
                headers={"User-Agent":"Mozilla/5.0"})
            # Extract <title> tags from RSS (skip first which is feed title)
            titles = re.findall(r'<title><!\[CDATA\[([^\]]+)\]\]></title>', r.text)
            if not titles:
                titles = re.findall(r'<title>([^<]{3,60})</title>', r.text)[1:]
            trending.extend(titles[:15])
            if trending: break
        except Exception as e:
            print(f"    Trends RSS error: {e}")
    return list(set(trending))[:20]

# ── Serper — Google US ────────────────────────────────────────────────────────
def serper(query):
    if not SERPER_KEY: return {}
    try:
        r = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY":SERPER_KEY,"Content-Type":"application/json"},
            json={"q":query,"num":10,"gl":"us","hl":"en"},
            timeout=15,
        )
        return r.json()
    except Exception as e:
        print(f"    Serper error: {e}"); return {}

def serper_suggestions(data):
    out = []
    for item in data.get("peopleAlsoAsk",[]): 
        if item.get("question"): out.append(item["question"])
    for item in data.get("relatedSearches",[]): 
        if item.get("query"): out.append(item["query"])
    return out[:15]

# ── Groq keyword expansion ────────────────────────────────────────────────────
def expand_keywords(seed, suggestions, trending):
    prompt = f"""You are an SEO keyword researcher for a US-focused blog about AI tools and automation for small businesses.

Seed topic: "{seed}"
Google related searches: {json.dumps(suggestions[:8])}
Today's trending US topics (use only if relevant): {json.dumps(trending[:8])}

Generate 20 specific long-tail keywords (4-8 words) mixing these content angles:
1. TOOL COMPARISONS: "X vs Y for [profession]"
2. INCOME/BUSINESS: "how to make money with X", "start a [business type] with AI"
3. PROFESSION-SPECIFIC: "best AI tools for [real estate agents / lawyers / coaches]"
4. WORKFLOW: "how to automate [specific task] for free"
5. TRENDING ANGLE: connect a trending topic to AI tools if relevant

For each keyword:
- article_type: "comparison" | "review" | "listicle" | "how-to" | "alternatives" | "income"
- affiliate_target: tool name or ""

Return ONLY valid JSON array, no markdown, no explanation:
[{{"keyword":"how to make money with zapier automations","article_type":"income","affiliate_target":"zapier"}}]"""

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
            json={"model":"llama-3.3-70b-versatile",
                  "messages":[{"role":"user","content":prompt}],
                  "max_tokens":1500,"temperature":0.6},
            timeout=45,
        )
        if r.status_code != 200: raise Exception(f"Groq {r.status_code}")
        text = r.json()["choices"][0]["message"]["content"]
        text = re.sub(r"```[a-z]*","",text).strip().strip("`")
        match = re.search(r"\[[\s\S]*\]", text)
        if match: return json.loads(match.group())
        return []
    except Exception as e:
        print(f"    Expansion error: {e}"); return []

# ── Helpers ───────────────────────────────────────────────────────────────────
TOOLS = ["zapier","notion","clickup","monday","calendly","hubspot","asana",
         "slack","airtable","make","trello","pipedrive","grammarly","chatgpt",
         "claude","midjourney","canva","shopify","webflow"]

def classify_type(kw):
    k = kw.lower()
    if " vs " in k:                                    return "comparison"
    if "alternative" in k:                             return "alternatives"
    if k.startswith("how to") or "tutorial" in k:     return "how-to"
    if k.startswith("best "):                          return "listicle"
    if any(w in k for w in ["make money","income","earn","business","startup"]): return "income"
    return "review"

def extract_tool(kw):
    k = kw.lower()
    for t in TOOLS:
        if t in k: return t
    return ""

_seen = set()

def save_keywords(keywords):
    saved = 0
    for kw in keywords:
        text = (kw.get("keyword") or "").strip().lower()
        if not text or len(text) < 10 or text in _seen: continue
        _seen.add(text)
        try:
            sb.table("keywords").insert({
                "keyword":           text,
                "article_type":      kw.get("article_type","review"),
                "affiliate_product": kw.get("affiliate_target",""),
                "status":            "pending",
            }).execute()
            saved += 1
        except Exception as e:
            err = str(e)
            if "duplicate" not in err.lower() and "unique" not in err.lower():
                print(f"    Insert error '{text[:40]}': {err[:80]}")
    return saved

# ── Seed topics — diverse angles ──────────────────────────────────────────────
SEEDS = [
    # Income/business angle — high engagement
    "make money with AI tools online",
    "start a business using AI automation",
    "freelance income with automation tools",
    "make money selling Zapier automations",
    "AI side hustle ideas for beginners",
    "start a social media agency with AI",
    "make money with Notion templates",
    "passive income with AI content tools",

    # Profession-specific — US focused
    "AI tools for real estate agents",
    "AI tools for freelance writers",
    "AI tools for marketing agencies",
    "AI tools for online coaches",
    "AI tools for ecommerce owners",
    "AI tools for accountants",
    "AI tools for consultants",
    "AI tools for photographers",

    # Tool comparisons — buyer intent
    "Zapier vs Make.com for small business",
    "Notion vs ClickUp for teams",
    "HubSpot vs Salesforce small business",
    "ChatGPT vs Claude for business writing",
    "Canva vs Adobe Express for marketing",

    # Alternatives — high search volume
    "Zapier alternatives free small business",
    "Notion alternatives for teams",
    "Mailchimp alternatives cheap",
    "QuickBooks alternatives freelancers",
    "Calendly alternatives free",

    # How-to workflow
    "how to automate invoicing small business",
    "how to automate social media for free",
    "how to use ChatGPT to write blog posts",
    "how to build a Notion client portal",
    "how to set up CRM free small business",
]

# ── Main ──────────────────────────────────────────────────────────────────────
def run():
    print(f"\n{'='*60}")
    print(f" Keyword Research  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f" Target: US  |  Seeds: {len(SEEDS)}  |  Angles: tools+income+business")
    print(f"{'='*60}\n")

    # Get today's trending topics once — used across all seeds
    print("Fetching Google Trends (US, free RSS)...")
    trending = get_trending_topics()
    print(f"  Got {len(trending)} trending topics: {trending[:5]}\n")

    total = 0
    for i, seed in enumerate(SEEDS):
        print(f"[{i+1}/{len(SEEDS)}] {seed}")
        try:
            data        = serper(seed)
            suggestions = serper_suggestions(data)
            keywords    = expand_keywords(seed, suggestions, trending)

            paa = [
                {"keyword": q.lower().rstrip("?").strip(),
                 "article_type": classify_type(q),
                 "affiliate_target": extract_tool(q)}
                for q in suggestions if 10 <= len(q) <= 80
            ]

            saved = save_keywords(keywords) + save_keywords(paa)
            total += saved
            print(f"      → {saved} new keywords\n")
        except Exception as e:
            print(f"      ERROR: {e}\n")
        time.sleep(1.2)

    print(f"{'='*60}")
    print(f" DONE. Total added: {total}")
    try:
        rows = sb.table("keywords").select("status").execute().data
        counts = {}
        for r in rows: counts[r["status"]] = counts.get(r["status"],0)+1
        print(f" Queue: {counts}")
    except: pass
    print(f"{'='*60}\n")

if __name__ == "__main__":
    run()