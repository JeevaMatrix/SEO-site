"""
Repair script — fixes broken YAML frontmatter in existing .md files.
Handles: amazon products injected into body, unclosed frontmatter, bad chars.

Usage:
    python scripts/repair_yaml.py
"""
import re, sys
from pathlib import Path

CONTENT_DIR = Path("src/content/blog")

def fix_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text

    # ── Case 1: frontmatter never closed (no second ---) ─────────────────
    # Happens when Groq wrote body content after frontmatter without closing ---
    if text.startswith("---"):
        # Find what should be the closing ---
        rest = text[3:]
        close_match = re.search(r'\n---\s*\n', rest)
        if not close_match:
            # No closing --- found — the whole file is broken
            # Strip everything, keep only recognizable frontmatter lines
            fm_lines = []
            body_start = 0
            for i, line in enumerate(rest.splitlines()):
                if re.match(r'^(title|description|pubDate|updatedDate|tags|image|affiliate|affiliateUrl|amazonProducts|draft):', line):
                    fm_lines.append(line)
                elif line.strip().startswith("- ") and fm_lines:
                    fm_lines.append(line)
                else:
                    body_start = i
                    break
            body = "\n".join(rest.splitlines()[body_start:])
            text = "---\n" + "\n".join(fm_lines) + "\namazonProducts: []\n---\n" + body

    # ── Case 2: amazonProducts block ended up inside the body ─────────────
    # Symptom: "| amazonProducts: []" in a table row, or amazon yaml in body
    text = re.sub(
        r'\|\s*amazonProducts:.*?(?=\n\||\n\n)',
        '',
        text,
        flags=re.DOTALL
    )
    # Strip orphaned amazon yaml lines floating in body
    text = re.sub(
        r'\n(amazonProducts:(?:\n  -[^\n]+)+)',
        '',
        text
    )

    # ── Case 3: bad amazonProducts in frontmatter ─────────────────────────
    fm_match = re.match(r'^---\r?\n(.*?)\n---\r?\n(.*)', text, re.DOTALL)
    if fm_match:
        fm_raw = fm_match.group(1)
        body   = fm_match.group(2)

        # Remove all existing amazonProducts lines from frontmatter
        fm_lines = fm_raw.splitlines()
        clean, skip = [], False
        for line in fm_lines:
            if line.startswith("amazonProducts:"):
                skip = True; continue
            if skip and (line.startswith("  -") or line.startswith("    ")):
                continue
            skip = False
            # Remove YAML comment lines
            if line.strip().startswith("#"):
                continue
            clean.append(line)

        # Fix title quoting
        for i, line in enumerate(clean):
            if line.startswith("title:"):
                m = re.match(r'title:\s*["\']?(.+?)["\']?\s*$', line)
                if m:
                    val = m.group(1).strip().strip('"').strip("'")
                    val = val.replace('"', "'")
                    if len(val) > 105:
                        val = val[:102].rsplit(" ",1)[0].rstrip(" :-—") + "..."
                    clean[i] = f'title: "{val}"'

        # Fix affiliateUrl quoting
        for i, line in enumerate(clean):
            if line.startswith("affiliateUrl:"):
                m = re.match(r'affiliateUrl:\s*["\']?(.+?)["\']?\s*$', line)
                if m:
                    val = m.group(1).strip().strip('"').strip("'")
                    clean[i] = f'affiliateUrl: "{val}"'

        clean.append("amazonProducts: []")
        text = "---\n" + "\n".join(clean) + "\n---\n" + body

    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False

def run():
    if not CONTENT_DIR.exists():
        print("Run from project root."); sys.exit(1)

    files = list(CONTENT_DIR.glob("*.md"))
    fixed, ok, errors = 0, 0, 0
    for f in files:
        try:
            if fix_file(f):
                print(f"  ✓ fixed  {f.name}")
                fixed += 1
            else:
                ok += 1
        except Exception as e:
            print(f"  ✗ error  {f.name}: {e}")
            errors += 1

    print(f"\n{fixed} fixed, {ok} already clean, {errors} errors")
    if fixed:
        print("Next: git add src/content/blog && git commit -m 'fix: yaml' && git push")

if __name__ == "__main__":
    run()