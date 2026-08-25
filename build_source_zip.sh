#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  Harvest Hero — Source ZIP Builder
#
#  Produces HarvestHero-<VERSION>.zip containing ONLY tracked
#  files from the git repo — no local secrets, no developer
#  inventory database, no dev tool folders.
#
#  Usage:
#    ./build_source_zip.sh
#
#  Output:
#    ../HarvestHero-<version>.zip   (one level up from this repo)
#
#  Because it uses `git archive`, anything that is:
#    - untracked (VercelToken/, OpenAI.env, data/, .devin/, ...)
#    - .gitignored
#  is guaranteed to be excluded, no matter what junk is sitting
#  in your working tree.
# ─────────────────────────────────────────────────────────────

set -euo pipefail
cd "$(dirname "$0")"

if ! command -v git >/dev/null; then
    echo "error: git is required" >&2
    exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
    echo "warning: working tree has uncommitted changes."
    echo "         git archive only includes committed files, so"
    echo "         anything unstaged will NOT be in the ZIP."
    echo
    read -r -p "Continue anyway? [y/N] " ans
    case "$ans" in
        y|Y|yes|YES) ;;
        *) echo "aborted." ; exit 1 ;;
    esac
fi

VERSION=$(python3 -c "import json; print(json.load(open('VERSION.json'))['version'])")
OUT="../HarvestHero-${VERSION}.zip"

echo "[build] Packaging Harvest Hero v${VERSION}..."
rm -f "$OUT"

# git archive respects .gitignore automatically and only includes
# tracked files. The prefix places everything under inventory_tracker/
# so end users' extract flow (`unzip HarvestHero-x.y.z.zip`) still
# produces the inventory_tracker/ folder they expect.
git archive \
    --format=zip \
    --prefix=inventory_tracker/ \
    -o "$OUT" \
    HEAD

echo "[build] Verifying no sensitive files leaked..."
LEAKS=$(unzip -Z1 "$OUT" | grep -E "(VercelToken|OpenAI\.env|/data/|\.devin/|\.vercel/|inventory\.db$|license\.json)" || true)
if [ -n "$LEAKS" ]; then
    echo "error: sensitive files found in ZIP:" >&2
    echo "$LEAKS" >&2
    exit 1
fi

SIZE=$(du -h "$OUT" | cut -f1)
COUNT=$(unzip -Z1 "$OUT" | wc -l | tr -d ' ')
echo
echo "  ✓ Built ${OUT}"
echo "    Size:  ${SIZE}"
echo "    Files: ${COUNT}"
echo
echo "  Upload this ZIP as a GitHub Release asset for v${VERSION}."
