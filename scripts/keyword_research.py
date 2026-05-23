"""
keyword_research.py — US-focused, Groq-powered, zero Anthropic dependency
Targets US small business owners searching for AI/automation tools.
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

GROQ_KEY     = os.environ.get("GROQ_API_KEY","")
SERPER_KEY   = os.environ.get("SERPER_API_KEY","")
SUPABASE_URL = os.environ.get("SUPABASE_URL","")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY","")
YEAR         = datetime.now().year

print("\n=== DIAGNOSTIC ===")
print(f"GROQ_API_KEY    : {'SET ✓' if GROQ_KEY else 'MISSING ✗'}")
print(f"SERPER_API_KEY  : {'SET ✓' if SERPER_KEY else 'MISSING (optional)'}")
print(f"SUPABASE_URL    : {SUPABASE_URL[:40]+'...' if len(SUPABASE_URL)>40 else SUPABASE_URL or 'MISSING ✗'}")
print(f"SUPABASE_KEY    : {'SET ✓' if SUPABASE_KEY else 'MISSING ✗'}")

if not GROQ_KEY:
    print("\nERROR: GROQ_API_KEY is missing. Get it free at console.groq.com")
    sys.exit(1)
if not SUPABASE_URL or not SUPABASE_KEY:
    print("\nERROR: SUPABASE_URL or SUPABASE_KEY missing.")
    sys.exit(1)

print("\n=== SUPABASE CONNECTION TEST ===")
try:
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("  Client created ✓")
except Exception as e:
    print(f"  Failed: {e}"); sys.exit(1)

try:
    result = sb.table("keywords").select("id").limit(1).execute()
    print(f"  'keywords' table OK ✓")
except Exception as e:
    err = str(e)
    print(f"  'keywords' table ERROR: {err}")
    if "PGRST125" in err or "relation" in err:
        print("""
  Run this SQL in Supabase → SQL Editor:

  create table if not exists keywords (
    id uuid default gen_random_uuid() primary key,
    keyword text not null unique,
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
    qa_score int,
    status text default 'draft',
    published_at timestamptz
  );
  create index if not exists idx_kw_status on keywords(status);
""")
    sys.exit(1)

try:
    sb.table("articles").select("id").limit(1).execute()
    print("  'articles' table OK ✓")
except Exception as e:
    print(f"  'articles' table missing — run the SQL above"); sys.exit(1)

print("\n  All tables OK. Starting keyword research...\n")

# ── Groq ──────────────────────────────────────────────────────────────────────
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

# ── Serper — US targeted ──────────────────────────────────────────────────────
def serper(query):
    if not SERPER_KEY:
        return {}
    try:
        r = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY":SERPER_KEY,"Content-Type":"application/json"},
            json={"q":query,"num":10,"gl":"us","hl":"en"},  # gl=us = Google US
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

# ── Keyword expansion ─────────────────────────────────────────────────────────
def expand_keywords(seed, suggestions):
    prompt = f"""You are an SEO keyword researcher targeting US small business owners.

Seed topic: "{seed}"
Related searches from Google US: {json.dumps(suggestions[:10])}

Generate 20 specific long-tail keywords (4-8 words each) that:
- Target US small business owners, freelancers, solopreneurs, or specific US professions
- Have clear buyer or research intent
- Are about AI tools, automation, productivity SaaS, or business software
- Use natural US English phrasing (e.g. "for small business" not "for SMB")

For each keyword specify:
- article_type: "comparison" | "review" | "listicle" | "how-to" | "alternatives"
- affiliate_target: tool name like "zapier" or "notion", or "" if none

Return ONLY a valid JSON array. No explanation. No markdown. Example:
[{{"keyword":"best zapier alternative for small business 2026","article_type":"alternatives","affiliate_target":"zapier"}}]"""

    try:
        text = groq(prompt)
        text = re.sub(r"```[a-z]*","",text).strip().strip("`")
        match = re.search(r"\[[\s\S]*\]", text)
        if match:
            return json.loads(match.group())
        return []
    except Exception as e:
        print(f"    Expansion error: {e}"); return []

# ── Helpers ───────────────────────────────────────────────────────────────────
TOOLS = ["zapier","notion","clickup","monday","calendly","hubspot","asana",
         "slack","airtable","make","trello","pipedrive","freshdesk","grammarly"]

def classify_type(kw):
    k = kw.lower()
    if " vs " in k:                               return "comparison"
    if "alternative" in k:                        return "alternatives"
    if k.startswith("how to") or "tutorial" in k: return "how-to"
    if k.startswith("best "):                     return "listicle"
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
        if not text or len(text) < 10 or text in _seen:
            continue
        _seen.add(text)
        try:
            sb.table("keywords").insert({
                "keyword":          text,
                "article_type":     kw.get("article_type","review"),
                "affiliate_product":kw.get("affiliate_target",""),
                "status":           "pending",
            }).execute()
            saved += 1
        except Exception as e:
            err = str(e)
            if "duplicate" in err.lower() or "unique" in err.lower():
                pass
            else:
                print(f"    Insert error '{text[:40]}': {err[:80]}")
    return saved

# ── US-focused seed topics ────────────────────────────────────────────────────
# Targeting high-intent US searches with buyer mindset
SEEDS = [
    # Tool alternatives — highest buyer intent
    "Zapier alternatives for small business",
    "Notion alternatives for teams",
    "ClickUp alternatives 2026",
    "Monday.com alternatives cheap",
    "HubSpot alternatives free CRM",
    "Asana alternatives small team",
    "Calendly alternatives free",
    "Grammarly alternatives free",
    "Mailchimp alternatives small business",
    "QuickBooks alternatives freelancers",

    # US profession-specific AI tools
    "AI tools for real estate agents",
    "AI tools for freelance writers",
    "AI tools for marketing agencies",
    "AI tools for online coaches",
    "AI tools for ecommerce store owners",
    "AI tools for accountants small business",
    "AI tools for consultants",
    "AI tools for lawyers solo practice",
    "AI tools for photographers",
    "AI tools for content creators",

    # How-to automation — US business context
    "how to automate invoicing small business",
    "how to automate social media posting free",
    "how to automate email follow up",
    "how to use Zapier for beginners",
    "how to set up CRM for small business",

    # Comparisons with US pricing context
    "Zapier vs Make.com for small business",
    "Notion vs ClickUp for teams",
    "HubSpot vs Salesforce small business",
    "Asana vs Monday for freelancers",
    "ChatGPT vs Claude for business writing",
]

# ── Main ──────────────────────────────────────────────────────────────────────
def run():
    print(f"{'='*58}")
    print(f" Keyword Research  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f" Target: US small business  |  Seeds: {len(SEEDS)}")
    print(f" AI: Groq FREE  |  SERP: Google US (gl=us)")
    print(f"{'='*58}\n")

    total = 0
    for i, seed in enumerate(SEEDS):
        print(f"[{i+1}/{len(SEEDS)}] {seed}")
        try:
            data        = serper(seed)
            suggestions = serper_suggestions(data)
            keywords    = expand_keywords(seed, suggestions)

            paa = [
                {"keyword": q.lower().rstrip("?").strip(),
                 "article_type": classify_type(q),
                 "affiliate_target": extract_tool(q)}
                for q in suggestions if 10 <= len(q) <= 80
            ]

            saved = save_keywords(keywords) + save_keywords(paa)
            total += saved
            print(f"      → {saved} new keywords saved\n")
        except Exception as e:
            print(f"      ERROR: {e}\n")
        time.sleep(1.0)

    print(f"{'='*58}")
    print(f" DONE. Total new keywords added this run: {total}")
    try:
        rows   = sb.table("keywords").select("status").execute().data
        counts = {}
        for r in rows:
            s = r["status"]; counts[s] = counts.get(s,0)+1
        print(f" Queue status: {counts}")
    except Exception:
        pass
    print(f"{'='*58}\n")

if __name__ == "__main__":
    run()