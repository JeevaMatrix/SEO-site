# Zero-Cost Programmatic SEO System
## AI Tools for Small Business Niche

Complete setup guide. Follow in order. Every command is tested and exact.

---

## 1. Prerequisites (5 min)

Install on your local machine:
- Node.js 18+ → https://nodejs.org
- Python 3.10+ → https://python.org
- Git → https://git-scm.com

---

## 2. Clone or init the project (2 min)

```bash
# Option A: Initialize fresh Astro project (recommended)
npm create astro@latest my-ai-tools-site
cd my-ai-tools-site

# Choose: "Blog" template, TypeScript: No, Install deps: Yes

# Option B: Clone this template directly
git clone https://github.com/YOURUSERNAME/YOURREPO.git
cd YOURREPO
npm install
```

---

## 3. Install dependencies (1 min)

```bash
# Astro integrations
npm install @astrojs/tailwind @astrojs/sitemap @astrojs/mdx

# Python deps (for automation scripts)
pip install anthropic supabase requests

# Dev server to preview locally
npm run dev   # → http://localhost:4321
```

---

## 4. Create accounts (15 min)

Do these in parallel (open all in separate tabs):

| Account | URL | What you get |
|---------|-----|-------------|
| GitHub | github.com | Code + Actions runner (free) |
| Vercel | vercel.com | Hosting (100GB free) |
| Supabase | supabase.com | Database (500MB free) |
| Anthropic | console.anthropic.com | $5 free AI credits |
| OpenAI | platform.openai.com | $5 free AI credits |
| Serper.dev | serper.dev | 2,500 free SERP searches/mo |
| Unsplash | unsplash.com/developers | Free image API |
| Google Search Console | search.google.com/search-console | Free indexing |
| Google Analytics | analytics.google.com | Free analytics |
| Cloudflare | cloudflare.com | Free CDN + DNS |

Affiliate networks (apply day 1, approval takes 1–7 days):
| Network | URL | Best for |
|---------|-----|---------|
| Amazon Associates | affiliate-program.amazon.com | Fast approval, broad products |
| PartnerStack | partnerstack.com | SaaS tools (Notion, ClickUp) |
| ShareASale | shareasale.com | Broad categories |
| Impact.com | impact.com | Premium SaaS brands |

---

## 5. Supabase setup (5 min)

1. Go to supabase.com → New project
2. Click "SQL Editor" → paste and run this:

```sql
create table keywords (
  id uuid default gen_random_uuid() primary key,
  keyword text not null,
  volume int,
  difficulty int,
  article_type text default 'review',
  affiliate_product text,
  status text default 'pending',
  created_at timestamptz default now()
);

create table articles (
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

create table affiliates (
  id uuid default gen_random_uuid() primary key,
  name text,
  url text,
  commission_rate text,
  network text,
  tracking_url text,
  active boolean default true
);

create table rank_history (
  id uuid default gen_random_uuid() primary key,
  article_id uuid references articles(id),
  rank int,
  checked_at timestamptz default now()
);

-- Index for faster queries
create index idx_keywords_status on keywords(status);
create index idx_articles_status on articles(status);
create index idx_articles_slug on articles(slug);
```

3. Go to Settings → API → copy "Project URL" and "anon public" key

---

## 6. GitHub Secrets (3 min)

In your GitHub repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret name | Value |
|-------------|-------|
| `ANTHROPIC_API_KEY` | From console.anthropic.com |
| `OPENAI_API_KEY` | From platform.openai.com |
| `SUPABASE_URL` | From Supabase Settings > API |
| `SUPABASE_KEY` | Supabase "anon public" key |
| `SERPER_API_KEY` | From serper.dev dashboard |
| `UNSPLASH_KEY` | From unsplash.com/developers |
| `SITE_URL` | Your Vercel URL (e.g. https://mysite.vercel.app) |
| `SITE_NAME` | Your site name (e.g. AI Tools Guide) |

---

## 7. Deploy to Vercel (3 min)

```bash
# Push to GitHub first
git add .
git commit -m "initial setup"
git push origin main

# Then:
# 1. Go to vercel.com
# 2. "New Project" → Import your GitHub repo
# 3. Framework: Astro (auto-detected)
# 4. Add environment variables:
#    SITE_URL = https://your-project.vercel.app
#    SITE_NAME = Your Site Name
# 5. Click Deploy
# Site is live in ~2 minutes
```

---

## 8. Run keyword research (first time — do manually)

```bash
# Set env vars locally
export SERPER_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
export SUPABASE_URL="your-url"
export SUPABASE_KEY="your-key"

# Run
python scripts/keyword_research.py

# Should add 300-500 keywords to your Supabase 'keywords' table
# Verify in Supabase → Table editor → keywords
```

---

## 9. Generate first articles (do manually to test quality)

```bash
export ARTICLES_PER_RUN=3

python scripts/content_generator.py
# Review the 3 files created in src/content/blog/
# Read each one. Adjust the prompt in content_generator.py if needed.
# Once satisfied → enable GitHub Actions automation
```

---

## 10. Enable GitHub Actions automation

Copy the workflow files to the correct paths:

```bash
# Create workflow directory
mkdir -p .github/workflows

# Create keyword research workflow
cat > .github/workflows/keyword-research.yml << 'EOF'
name: Daily keyword research
on:
  schedule:
    - cron: '0 6 * * *'
  workflow_dispatch:
jobs:
  research:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install anthropic supabase requests
      - name: Run keyword research
        env:
          SERPER_API_KEY: ${{ secrets.SERPER_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
        run: python scripts/keyword_research.py
EOF

# Create content generator workflow
cat > .github/workflows/content-generator.yml << 'EOF'
name: Daily content generator
on:
  schedule:
    - cron: '0 8 * * *'
  workflow_dispatch:
jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install anthropic supabase requests
      - run: |
          git config user.email "bot@yoursite.com"
          git config user.name "ContentBot"
      - name: Generate content
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          UNSPLASH_KEY: ${{ secrets.UNSPLASH_KEY }}
          SITE_URL: ${{ secrets.SITE_URL }}
          ARTICLES_PER_RUN: "5"
        run: python scripts/content_generator.py
EOF

# Create weekly SEO workflow
cat > .github/workflows/weekly-seo.yml << 'EOF'
name: Weekly SEO maintenance
on:
  schedule:
    - cron: '0 9 * * 0'
  workflow_dispatch:
jobs:
  seo:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install anthropic supabase requests
      - run: |
          git config user.email "bot@yoursite.com"
          git config user.name "SEOBot"
      - name: Check rankings
        env:
          SERPER_API_KEY: ${{ secrets.SERPER_API_KEY }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          SITE_URL: ${{ secrets.SITE_URL }}
        run: python scripts/rank_tracker.py
      - name: Add internal links
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
        run: python scripts/internal_linker.py
      - name: Validate affiliates
        run: python scripts/affiliate_validator.py
        continue-on-error: true
      - uses: actions/upload-artifact@v4
        with:
          name: seo-reports
          path: "*.txt\n*.json"
EOF

git add .github/
git commit -m "add: GitHub Actions automation workflows"
git push
```

---

## 11. Weekly review checklist (30 min/week after setup)

Every Sunday, check these 5 things:

1. **GitHub Actions** → Did all workflows run without errors?
2. **Google Search Console** → How many pages indexed this week? Any manual actions?
3. **Supabase** → Articles table: how many published? Keywords: how many pending?
4. **Affiliate dashboards** → Any clicks? Any commissions?
5. **Google Analytics** → Sessions, top pages, traffic sources

If everything is green: close laptop. System is running itself.

---

## 12. Cost tracker

| Item | Cost | Notes |
|------|------|-------|
| GitHub + GitHub Actions | $0 | Free for public repos |
| Vercel hosting | $0 | 100GB bandwidth free |
| Supabase | $0 | 500MB storage free |
| Cloudflare CDN | $0 | Free plan covers everything |
| Anthropic API | $0* | $5 free credit = ~500 articles |
| OpenAI API | $0* | $5 free credit = ~1000 articles |
| Serper.dev | $0 | 2,500 searches/mo free |
| Unsplash API | $0 | Unlimited free |
| Google Analytics | $0 | Free |
| Google Search Console | $0 | Free |
| Brevo email | $0 | 300 emails/day free |
| **TOTAL MONTH 1** | **$0** | After free credits run out: ~$20/mo for AI |
| Domain (month 2+) | $10/year | Only once validated |

---

## Troubleshooting

**Articles not publishing?**
- Check GitHub Actions logs (repo → Actions tab)
- Check Supabase keywords table: any with status='pending'?
- Check ARTICLES_PER_RUN env var is set

**GitHub Actions failing?**
- Click the failed run → expand the failing step → copy error to Google

**Articles not indexing?**
- New domains take 2–6 weeks for first index
- Use GSC URL Inspection → "Request indexing" on key pages manually
- Ensure sitemap is submitted in GSC

**QA score too low?**
- Edit the prompt in content_generator.py
- Key fix: make sure keyword appears in first 200 words
- Run locally with ARTICLES_PER_RUN=1 to test changes fast

---

## Scaling checklist (Month 2+)

- [ ] 100+ articles published
- [ ] First pages indexed in GSC
- [ ] Ezoic account approved and ads active
- [ ] At least 2 affiliate programs approved
- [ ] Email list growing (even 50 subs = validation)
- [ ] Rank tracker showing first positions
- [ ] ARTICLES_PER_RUN increased to 10/day
- [ ] Site 2 in a second niche planned
