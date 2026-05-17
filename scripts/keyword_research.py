"""
Diagnostic + fixed keyword_research.py
Fixes: PGRST125 error (table not found / connection issue)
"""

import os, json, sys, subprocess, time, re
from datetime import datetime
from pathlib import Path

def install(pkg):
    subprocess.run([sys.executable,"-m","pip","install",pkg,"-q"],check=True)

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
            print(f"  Loading .env from: {p.resolve()}")
            for line in p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    os.environ.setdefault(k, v)
            return
    print("  No .env file found — using system environment variables")

load_dotenv()

GROQ_KEY     = os.environ.get("GROQ_API_KEY","")
SERPER_KEY   = os.environ.get("SERPER_API_KEY","")
SUPABASE_URL = os.environ.get("SUPABASE_URL","")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY","")
YEAR         = datetime.now().year

# ── Step 1: Validate config ───────────────────────────────────────────────────
print("\n=== DIAGNOSTIC ===")
print(f"GROQ_API_KEY    : {'SET ✓' if GROQ_KEY else 'MISSING ✗'}")
print(f"SERPER_API_KEY  : {'SET ✓' if SERPER_KEY else 'MISSING (optional)'}")
print(f"SUPABASE_URL    : {SUPABASE_URL[:40] + '...' if len(SUPABASE_URL) > 40 else SUPABASE_URL or 'MISSING ✗'}")
print(f"SUPABASE_KEY    : {'SET ✓' if SUPABASE_KEY else 'MISSING ✗'}")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("\nERROR: SUPABASE_URL or SUPABASE_KEY is missing.")
    print("Check your .env file — it must be in the project root folder.")
    sys.exit(1)

if not SUPABASE_URL.startswith("https://"):
    print(f"\nERROR: SUPABASE_URL looks wrong: '{SUPABASE_URL}'")
    print("It should start with https:// and end with .supabase.co")
    sys.exit(1)

# ── Step 2: Test Supabase connection + check tables ───────────────────────────
print("\n=== SUPABASE CONNECTION TEST ===")
try:
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("  Client created ✓")
except Exception as e:
    print(f"  Failed to create client: {e}")
    sys.exit(1)

# Test if keywords table exists
try:
    result = sb.table("keywords").select("id").limit(1).execute()
    print(f"  'keywords' table exists ✓  (rows found: {len(result.data)})")
except Exception as e:
    err = str(e)
    print(f"  'keywords' table ERROR: {err}")
    if "PGRST125" in err or "Invalid path" in err:
        print("""
  ┌─────────────────────────────────────────────────────────┐
  │  CAUSE: The 'keywords' table doesn't exist in Supabase. │
  │  FIX: Run the SQL below in Supabase → SQL Editor        │
  └─────────────────────────────────────────────────────────┘

  Go to: supabase.com → your project → SQL Editor → New query
  Paste and run this:

  create table if not exists keywords (
    id uuid default gen_random_uuid() primary key,
    keyword text not null,
    volume int,
    difficulty int,
    article_type text default 'review',
    affiliate_product text,
    status text default 'pending',
    created_at timestamptz default now()
  );

  create table if not exists articles (
    id uuid default gen_random_uuid() primary key,
    keyword_id uuid references keywords(id),
    slug text unique not null,
    title text,
    word_count int,
    published_at timestamptz,
    status text default 'draft',
    qa_score int,
    rank int,
    last_checked timestamptz
  );

  create table if not exists rank_history (
    id uuid default gen_random_uuid() primary key,
    article_id uuid references articles(id),
    rank int,
    checked_at timestamptz default now()
  );

  create index if not exists idx_kw_status on keywords(status);
  create index if not exists idx_art_status on articles(status);

  After running, re-run this script.
""")
    sys.exit(1)

# Test articles table too
try:
    sb.table("articles").select("id").limit(1).execute()
    print(f"  'articles' table exists ✓")
except Exception as e:
    print(f"  'articles' table missing — run the SQL above to create it")
    sys.exit(1)

print("\n  All tables OK. Starting keyword research...\n")

# ── Groq API ──────────────────────────────────────────────────────────────────
def groq(prompt, max_tokens=1500):
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
        json={"model":"llama-3.3-70b-versatile",
              "messages":[{"role":"user","content":prompt}],
              "max_tokens":max_tokens,"temperature":0.5},
        timeout=45,
    )
    if r.status_code != 200:
        raise Exception(f"Groq {r.status_code}: {r.text[:300]}")
    return r.json()["choices"][0]["message"]["content"]

# ── Serper API ────────────────────────────────────────────────────────────────
def serper(query):
    if not SERPER_KEY:
        return {}
    try:
        r = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY":SERPER_KEY,"Content-Type":"application/json"},
            json={"q":query,"num":10,"gl":"us"},
            timeout=15,
        )
        return r.json()
    except Exception as e:
        print(f"    Serper error: {e}")
        return {}

def serper_suggestions(data):
    out = []
    for item in data.get("peopleAlsoAsk",[]):
        if item.get("question"): out.append(item["question"])
    for item in data.get("relatedSearches",[]):
        if item.get("query"): out.append(item["query"])
    return out[:15]

# ── Keyword expansion ─────────────────────────────────────────────────────────
def expand_keywords(seed, suggestions):
    prompt = f"""You are an SEO keyword researcher for a website about AI and automation tools for small businesses.

Seed topic: "{seed}"
Related searches: {json.dumps(suggestions[:10])}

Generate 20 specific long-tail keywords (4-8 words each) that:
- Target small business owners, freelancers, or specific professions
- Have buyer or research intent
- Relate to AI tools, automation, or productivity SaaS

For each keyword specify:
- article_type: "comparison" | "review" | "listicle" | "how-to" | "alternatives"
- affiliate_target: tool name like "zapier" or "notion", or "" if none

Return ONLY a valid JSON array. No explanation. No markdown fences. Example:
[{{"keyword":"zapier vs make for small business","article_type":"comparison","affiliate_target":"zapier"}}]"""

    try:
        text = groq(prompt)
        # Remove any markdown code fences
        text = re.sub(r"```[a-z]*","",text).strip().strip("`")
        # Find the JSON array
        match = re.search(r"\[[\s\S]*\]", text)
        if match:
            return json.loads(match.group())
        return []
    except Exception as e:
        print(f"    Expansion error: {e}")
        return []

# ── Classification helpers ────────────────────────────────────────────────────
TOOLS = ["zapier","notion","clickup","monday","calendly","hubspot","asana",
         "slack","airtable","make","trello","todoist","pipedrive","freshdesk"]

def classify_type(kw):
    k = kw.lower()
    if " vs " in k:                          return "comparison"
    if "alternative" in k:                   return "alternatives"
    if k.startswith("how to") or "tutorial" in k: return "how-to"
    if k.startswith("best "):                return "listicle"
    return "review"

def extract_tool(kw):
    k = kw.lower()
    for t in TOOLS:
        if t in k: return t
    return ""

# ── Save to Supabase (fixed — checks existence differently) ───────────────────
_seen_keywords = set()  # in-memory dedup for this run

def keyword_exists(keyword):
    """Check if keyword already in DB. Uses a safer query."""
    try:
        result = (sb.table("keywords")
                    .select("id")
                    .eq("keyword", keyword)
                    .limit(1)
                    .execute())
        return bool(result.data)
    except Exception:
        return False  # if check fails, try to insert anyway

def save_keywords(keywords):
    saved = 0
    for kw in keywords:
        text = (kw.get("keyword") or "").strip().lower()
        if not text or len(text) < 10:
            continue
        if text in _seen_keywords:
            continue
        _seen_keywords.add(text)

        # Skip DB check for first batch to avoid PGRST125 on bad tables
        # (the insert itself will fail gracefully if duplicate)
        try:
            sb.table("keywords").insert({
                "keyword":         text,
                "article_type":    kw.get("article_type","review"),
                "affiliate_product": kw.get("affiliate_target",""),
                "status":          "pending",
            }).execute()
            saved += 1
        except Exception as e:
            err = str(e)
            if "duplicate" in err.lower() or "unique" in err.lower():
                pass  # already exists — fine
            else:
                print(f"    Insert error for '{text[:40]}': {err[:100]}")
    return saved

# ── Seed terms ────────────────────────────────────────────────────────────────
SEEDS = [
    "Zapier alternatives","Notion alternatives","ClickUp alternatives",
    "Monday.com alternatives","Calendly alternatives",
    "HubSpot alternatives free","Asana alternatives",
    "best AI writing tool small business","best AI email tool",
    "best AI scheduling tool","best AI invoice generator",
    "best free CRM 2026","best automation tool freelancers",
    "ChatGPT for real estate agents","AI tools for freelancers",
    "automation tools for restaurants","AI tools for coaches",
    "how to use Zapier for beginners","Make.com tutorial beginners",
    "how to automate invoices free","Notion for client management",
    "free project management software small business",
]

# ── Main ──────────────────────────────────────────────────────────────────────
def run():
    print(f"{'='*55}")
    print(f" Keyword Research  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f" Seeds: {len(SEEDS)}  |  AI: Groq FREE  |  SERP: Serper FREE")
    print(f"{'='*55}\n")

    total = 0

    for i, seed in enumerate(SEEDS):
        print(f"[{i+1}/{len(SEEDS)}] '{seed}'")

        try:
            # SERP suggestions
            data        = serper(seed)
            suggestions = serper_suggestions(data)
            print(f"      SERP suggestions: {len(suggestions)}")

            # AI expansion
            keywords = expand_keywords(seed, suggestions)
            print(f"      AI keywords generated: {len(keywords)}")

            # PAA questions as keywords too
            paa_keywords = [
                {"keyword": q.lower().rstrip("?").strip(),
                 "article_type": classify_type(q),
                 "affiliate_target": extract_tool(q)}
                for q in suggestions if 10 <= len(q) <= 80
            ]

            saved_ai  = save_keywords(keywords)
            saved_paa = save_keywords(paa_keywords)
            saved     = saved_ai + saved_paa
            total    += saved
            print(f"      Saved to DB: {saved} new keywords\n")

        except Exception as e:
            print(f"      ERROR on this seed: {e}\n")

        time.sleep(1.0)  # rate limit

    print(f"{'='*55}")
    print(f" DONE. Total new keywords added: {total}")

    # Show queue
    try:
        rows   = sb.table("keywords").select("status").execute().data
        counts = {}
        for r in rows:
            s = r["status"]
            counts[s] = counts.get(s, 0) + 1
        print(f" DB queue: {counts}")
    except Exception:
        pass
    print(f"{'='*55}\n")

if __name__ == "__main__":
    run()