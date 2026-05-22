"""
repair_yaml.py — fixes broken frontmatter in all blog .md files.
Run locally before pushing whenever you see YAML parse errors on Vercel.

Usage:
    python scripts/repair_yaml.py

What it fixes:
  - amazonProducts block injected into article body instead of frontmatter
  - Entire frontmatter collapsed onto one line (col 244 style error)
  - Unclosed frontmatter (missing second ---)
  - Unquoted or badly quoted title / affiliateUrl values
  - YAML comment lines (#) inside frontmatter
  - Stale/malformed amazonProducts entries
"""
import re, sys
from pathlib import Path

CONTENT_DIR = Path("src/content/blog")

def _ys(v: str) -> str:
    return str(v).replace("\\", "\\\\").replace('"', "'").replace("\n", " ").strip()

def split_frontmatter(text: str):
    """Returns (fm_text, body) or (None, text) if no valid frontmatter."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.startswith("---"):
        return None, text
    m = re.search(r"\n---\s*(?:\n|$)", text[3:])
    if not m:
        return None, text
    fm_end     = 3 + m.start()
    body_start = 3 + m.end()
    return text[3:fm_end], text[body_start:]

def clean_frontmatter(fm_text: str, slug: str = "") -> str:
    """
    Cleans and rebuilds frontmatter text:
    - Removes comment lines
    - Removes stale amazonProducts block
    - Fixes title + affiliateUrl quoting
    - Adds amazonProducts: [] if missing
    """
    lines = fm_text.splitlines()
    clean, skip, has_amazon = [], False, False

    for line in lines:
        if line.strip().startswith("#"):
            continue
        if line.startswith("amazonProducts:"):
            skip = True
            has_amazon = True
            clean.append("amazonProducts: []")   # placeholder — proper inject later
            continue
        if skip:
            if line.startswith("  ") or line.startswith("\t"):
                continue
            else:
                skip = False
        # Fix title
        if line.startswith("title:"):
            m = re.match(r'title:\s*["\']?(.+?)["\']?\s*$', line)
            if m:
                val = m.group(1).strip().strip('"').strip("'")
                if len(val) > 105:
                    val = val[:102].rsplit(" ", 1)[0].rstrip(" :-—") + "..."
                line = f'title: "{_ys(val)}"'
        # Fix description — pad if too short for SEO
        if line.startswith("description:"):
            m = re.match(r'description:\s*["\'\']?(.+?)["\'\']?\s*$', line)
            if m:
                val = m.group(1).strip().strip('"').strip("'")
                if len(val) < 80:
                    val = val.rstrip('.') + '. An in-depth guide to help small business owners choose the right AI tools and automation software.'
                if len(val) > 160:
                    val = val[:157].rsplit(' ', 1)[0].rstrip(' .,') + '.'
                line = f'description: "{_ys(val)}"'

        # Fix affiliateUrl
        if line.startswith("affiliateUrl:"):
            m = re.match(r'affiliateUrl:\s*(.+)\s*$', line)
            if m:
                val = _ys(m.group(1).strip().strip('"').strip("'"))
                line = f'affiliateUrl: "{val}"'
        clean.append(line)

    if not has_amazon:
        clean.append("amazonProducts: []")

    return "\n".join(clean)

def fix_body(body: str) -> str:
    """Remove orphaned amazonProducts YAML that ended up in article body."""
    # Table row containing amazonProducts
    body = re.sub(r'\|\s*amazonProducts:.*?(?=\n\||\n\n|\Z)', '', body, flags=re.DOTALL)
    # Orphaned block-style amazonProducts in body
    body = re.sub(r'\namazonProducts:(?:\n  -[^\n]+)+', '', body)
    # Orphaned single-line
    body = re.sub(r'\namazonProducts: \[\]', '', body)
    return body

def fix_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    fm_text, body = split_frontmatter(text)

    if fm_text is None:
        # No frontmatter at all — very broken, build minimal
        slug = path.stem
        fm_text = (
            f'title: "{slug.replace("-", " ").title()}"\n'
            f'description: "A guide to {slug.replace("-", " ")}."\n'
            f'pubDate: 2026-05-22\n'
            f'tags: ["ai tools", "small business"]\n'
            f'affiliate: ""\naffiliateUrl: ""'
        )
        body = text

    fm_clean = clean_frontmatter(fm_text, path.stem)
    body_clean = fix_body(body)

    final = f"---\n{fm_clean}\n---\n{body_clean}"

    if final != original:
        path.write_text(final, encoding="utf-8")
        return True
    return False

def run():
    if not CONTENT_DIR.exists():
        print("Run from project root (where src/ is)."); sys.exit(1)

    files = sorted(CONTENT_DIR.glob("*.md"))
    print(f"Checking {len(files)} files...\n")

    fixed, ok, errors = 0, 0, 0
    for f in files:
        try:
            if fix_file(f):
                print(f"  ✓ fixed   {f.name}")
                fixed += 1
            else:
                ok += 1
        except Exception as e:
            print(f"  ✗ error   {f.name}: {e}")
            errors += 1

    print(f"\nResult: {fixed} fixed | {ok} clean | {errors} errors")
    if fixed:
        print("\nNext steps:")
        print("  git add src/content/blog")
        print('  git commit -m "fix: repair yaml frontmatter"')
        print("  git push")

if __name__ == "__main__":
    run()