#!/usr/bin/env bash
set -ex
set -o pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null && pwd)"

SOURCE_DIR="$(git -C "$DIR" rev-parse --show-toplevel)"
python3 "$SOURCE_DIR/tools/vendor/check.py"
python3 "$SOURCE_DIR/tools/release/stage_mapd_provider.py" --source "$SOURCE_DIR"
if [ -z "$TARGET_DIR" ]; then
  TARGET_DIR="$(mktemp -d)"
fi

# set git identity
source "$DIR/identity.sh"

echo "[-] Setting up target repo T=$SECONDS"

mkdir -p "$TARGET_DIR"
if [ -n "$(find "$TARGET_DIR" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
  echo "TARGET_DIR must be empty: $TARGET_DIR"
  exit 1
fi
cd "$TARGET_DIR"
# Independent metadata also supports sources whose .git is a worktree file.
git init --initial-branch=tmp
if ORIGIN_URL="$(git -C "$SOURCE_DIR" remote get-url origin)"; then
  git remote add origin "$ORIGIN_URL"
fi

# do the files copy
echo "[-] copying files T=$SECONDS"
cd "$SOURCE_DIR"
./tools/release/release_files.py | xargs -0 cp -pR --parents -t "$TARGET_DIR" --
python3 "$SOURCE_DIR/tools/release/stage_mapd_provider.py" --source "$SOURCE_DIR" --destination "$TARGET_DIR"

# in the directory
cd "$TARGET_DIR"


# include source commit hash and build date in commit
GIT_HASH=$(git -C "$SOURCE_DIR" rev-parse HEAD)
GIT_COMMIT_DATE=$(git -C "$SOURCE_DIR" show --no-patch --format='%ct %ci' HEAD)
DATETIME=$(date '+%Y-%m-%dT%H:%M:%S')
VERSION=$(cat "$SOURCE_DIR/openpilot/common/version.h" | awk -F\" '{print $2}')

echo -n "$GIT_HASH" > git_src_commit
echo -n "$GIT_COMMIT_DATE" > git_src_commit_date

echo "[-] committing version $VERSION T=$SECONDS"
# writing larger objects is faster than compressing them on-device
git -c core.compression=0 add -f .
git status
git -c core.compression=0 commit -a -m "openpilot v$VERSION release

date: $DATETIME
master commit: $GIT_HASH
"

# Check packaged dependency layout and reject pointer payloads.
python3 tools/vendor/check.py --revision HEAD
python3 tools/resources/check.py --revision HEAD

source "$SOURCE_DIR/tools/release/check_file_sizes.sh"

if [ ! -z "$BRANCH" ]; then
  echo "[-] Pushing to $BRANCH T=$SECONDS"
  # uploading the larger pack is faster than spending CPU to optimize it
  git -c pack.window=0 -c pack.depth=0 -c pack.compression=0 push -f origin "tmp:$BRANCH"
fi

echo "[-] done T=$SECONDS, ready at $TARGET_DIR"
