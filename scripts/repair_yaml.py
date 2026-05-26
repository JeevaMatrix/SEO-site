"""
repair_yaml.py — nuclear YAML repair for all blog .md files.
Handles every known gray-matter parse error pattern.

Fixes:
  - bad indentation of a mapping entry
  - multiline key / implicit key errors
  - amazonProducts injected into body
  - collapsed single-line frontmatter
  - unclosed frontmatter (missing second ---)
  - unquoted / badly quoted values
  - YAML comment lines (#) inside frontmatter
  - stale/malformed amazonProducts entries
  - tags list formatting errors
  - leading/trailing whitespace on field values
  - mixed indentation (tabs + spaces)
  - colon-in-value without quoting

Usage:
    python scripts/repair_yaml.py
"""
import re, sys
from pathlib import Path

CONTENT_DIR = Path("src/content/blog")

# ── YAML-safe string ──────────────────────────────────────────────────────────
def _ys(v: str) -> str:
    """Make value safe for YAML double-quoted scalar."""
    v = str(v)
    v = v.replace("\\", "\\\\")   # backslash first
    v = v.replace('"', "'")        # no double quotes inside double-quoted string
    v = v.replace("\n", " ").replace("\r", " ")  # no newlines
    v = v.replace("\t", " ")       # no tabs
    return v.strip()

# ── Split frontmatter from body ───────────────────────────────────────────────
def split_frontmatter(text: str):
    """
    Returns (fm_text, body) or (None, text).
    Handles: missing trailing newline, collapsed frontmatter, \\r\\n.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.startswith("---"):
        return None, text
    # Find closing --- on its own line
    m = re.search(r"\n---\s*(?:\n|$)", text[3:])
    if not m:
        return None, text
    fm_end     = 3 + m.start()
    body_start = 3 + m.end()
    return text[3:fm_end], text[body_start:]

# ── Known scalar fields ───────────────────────────────────────────────────────
SCALAR_FIELDS = {"title", "description", "pubDate", "updatedDate",
                 "image", "affiliate", "affiliateUrl", "draft"}
LIST_FIELDS   = {"tags", "amazonProducts"}

# ── Nuclear frontmatter rebuilder ─────────────────────────────────────────────
def rebuild_frontmatter(fm_text: str, slug: str = "") -> str:
    """
    Complete rebuild strategy:
    1. Try to extract key:value pairs from every line regardless of indentation
    2. Discard structurally broken lines
    3. Rebuild cleanly with correct quoting and indentation
    """
    # Replace tabs with spaces first
    fm_text = fm_text.replace("\t", "  ")

    lines = fm_text.splitlines()

    # ── Pass 1: extract all recognizable key:value pairs ─────────────────────
    extracted = {}   # key → raw value string
    current_key  = None
    current_val  = []
    in_block     = False   # inside amazonProducts or tags block

    for line in lines:
        stripped = line.strip()

        # Skip comment lines
        if stripped.startswith("#"):
            continue

        # Skip empty lines
        if not stripped:
            continue

        # Detect a top-level key: value line (no leading spaces on the key)
        # Matches: key: value  OR  key:  (empty value)
        top_key_match = re.match(r'^([a-zA-Z][a-zA-Z0-9_]*):\s*(.*)', stripped)

        if top_key_match and not line.startswith(" ") and not line.startswith("\t"):
            # Save previous key
            if current_key and current_val:
                extracted[current_key] = " ".join(current_val).strip()
            current_key = top_key_match.group(1)
            current_val = [top_key_match.group(2).strip()]
            in_block = current_key in LIST_FIELDS
        elif in_block and (line.startswith("  ") or line.startswith("- ")):
            # Continuation of a list block
            current_val.append(stripped)
        elif current_key and line.startswith(" ") and current_key not in LIST_FIELDS:
            # Continuation of a scalar (multiline value — flatten it)
            current_val.append(stripped)
        # else: orphaned line, discard

    # Save last key
    if current_key and current_val:
        extracted[current_key] = " ".join(current_val).strip()

    # ── Pass 2: build clean frontmatter lines ─────────────────────────────────
    clean = []

    # title
    title = extracted.get("title", slug.replace("-", " ").title())
    title = title.strip().strip('"').strip("'")
    if len(title) > 105:
        title = title[:102].rsplit(" ", 1)[0].rstrip(" :-—") + "..."
    clean.append(f'title: "{_ys(title)}"')

    # description
    desc = extracted.get("description", f"A guide to {slug.replace('-', ' ')}.")
    desc = desc.strip().strip('"').strip("'")
    if len(desc) < 80:
        desc = desc.rstrip('.') + '. An in-depth guide to help small business owners choose the right AI tools.'
    if len(desc) > 160:
        desc = desc[:157].rsplit(' ', 1)[0].rstrip(' .,') + '.'
    clean.append(f'description: "{_ys(desc)}"')

    # pubDate
    pub = extracted.get("pubDate", "2026-05-22")
    pub = re.sub(r'[^0-9-]', '', pub.strip().strip('"').strip("'"))[:10]
    if not re.match(r'\d{4}-\d{2}-\d{2}', pub):
        pub = "2026-05-22"
    clean.append(f'pubDate: {pub}')

    # updatedDate (optional)
    if "updatedDate" in extracted:
        upd = re.sub(r'[^0-9-]', '', extracted["updatedDate"].strip().strip('"').strip("'"))[:10]
        if re.match(r'\d{4}-\d{2}-\d{2}', upd):
            clean.append(f'updatedDate: {upd}')

    # image
    image = extracted.get("image", "")
    image = image.strip().strip('"').strip("'")
    if image and image != "PLACEHOLDER_IMAGE":
        clean.append(f'image: "{_ys(image)}"')

    # tags — rebuild as proper YAML list
    tags_raw = extracted.get("tags", '["ai tools", "small business"]')
    # Extract individual tag values
    tag_vals = re.findall(r'"([^"]+)"|\'([^\']+)\'|(\w[\w\s-]+\w)', tags_raw)
    tags = [next(v for v in t if v) for t in tag_vals]
    if not tags:
        tags = ["ai tools", "small business"]
    tags_str = ", ".join(f'"{t}"' for t in tags[:5])
    clean.append(f'tags: [{tags_str}]')

    # affiliate
    aff = extracted.get("affiliate", "")
    clean.append(f'affiliate: "{_ys(aff.strip().strip(chr(34)).strip(chr(39)))}"')

    # affiliateUrl
    aff_url = extracted.get("affiliateUrl", "")
    aff_url = aff_url.strip().strip('"').strip("'")
    clean.append(f'affiliateUrl: "{_ys(aff_url)}"')

    # draft
    draft = extracted.get("draft", "false")
    draft = "true" if str(draft).strip().lower() == "true" else "false"
    clean.append(f'draft: {draft}')

    # amazonProducts — always reset to [] (backfill handles proper values)
    clean.append("amazonProducts: []")

    return "\n".join(clean)

# ── Fix body ──────────────────────────────────────────────────────────────────
def fix_body(body: str) -> str:
    """Remove orphaned amazonProducts YAML from article body."""
    body = re.sub(r'\|\s*amazonProducts:.*?(?=\n\||\n\n|\Z)', '', body, flags=re.DOTALL)
    body = re.sub(r'\namazonProducts:(?:\n[ \t]+-[^\n]*)+', '', body)
    body = re.sub(r'\namazonProducts:\s*\[\]', '', body)
    # Remove orphaned YAML scalar lines in body (price: "xxx", url: "xxx" etc.)
    body = re.sub(r'\n[ \t]+(price|url|cat|asin):\s*"[^"]*"', '', body)
    return body

# ── Per-file fix ──────────────────────────────────────────────────────────────
def fix_file(path: Path) -> tuple[bool, str]:
    """Returns (changed, reason)."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"read error: {e}"

    original = text
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    fm_text, body = split_frontmatter(text)

    if fm_text is None:
        # No valid frontmatter found at all — build from scratch
        fm_text = ""
        body = text
        reason = "no frontmatter"
    else:
        reason = "frontmatter found"

    # Always rebuild frontmatter from scratch — nuclear approach
    # This handles indentation, quoting, and structural errors in one pass
    fm_clean   = rebuild_frontmatter(fm_text, path.stem)
    body_clean = fix_body(body)

    final = f"---\n{fm_clean}\n---\n{body_clean}"

    if final != original:
        try:
            path.write_text(final, encoding="utf-8")
            return True, reason
        except Exception as e:
            return False, f"write error: {e}"
    return False, "already clean"

# ── Main ──────────────────────────────────────────────────────────────────────
def run():
    if not CONTENT_DIR.exists():
        print("ERROR: Run from project root (where src/ is).")
        sys.exit(1)

    files = sorted(CONTENT_DIR.glob("*.md"))
    print(f"Repairing {len(files)} files...\n")

    fixed, ok, errors = 0, 0, 0
    for f in files:
        changed, reason = fix_file(f)
        if changed:
            print(f"  ✓ fixed   {f.name}  ({reason})")
            fixed += 1
        elif reason.startswith("read error") or reason.startswith("write error"):
            print(f"  ✗ error   {f.name}  ({reason})")
            errors += 1
        else:
            ok += 1

    print(f"\nResult: {fixed} fixed | {ok} clean | {errors} errors")

    if fixed:
        print("\nNext:")
        print("  git add src/content/blog")
        print('  git commit -m "fix: repair yaml frontmatter"')
        print("  git push")

if __name__ == "__main__":
    run()