# Tracked dependency sources

Dependencies are ordinary folders in this repository. Clone normally, run
`tools/op.sh setup`, and commit application and dependency edits together.

`upstream-sync.json` records the last integrated upstream commit and its pristine
tree for each dependency. A recorded tree identifies the merge base; it does not
claim that the current folder is unchanged. Optional import exclusions are
explicit. Required third-party license notices remain in the source folders.

Run `python3 tools/vendor/check.py` to validate the tracked working tree, or add
`--revision REV` to validate a fetched commit before checking it out. Validation
checks layout and provenance fields; it does not establish runtime compatibility.

Maintainers can preview a dependency update with:

```sh
python3 tools/vendor/sync.py panda FULL_UPSTREAM_COMMIT_HASH
```

The base is the previously integrated snapshot, ours is the committed local
folder, and theirs is the selected upstream snapshot. The command requires a
clean checkout. It downloads objects into an external cache, reports conflicts
without changing the checkout, and preserves local edits through a three-way
merge. Use `--source-repo /path/to/upstream/repo` for an existing local object
cache. Add `--apply` to stage a conflict-free result and updated manifest. Review
the diff, run the affected tests, and create one ordinary local commit. The tool
does not commit, push, or resolve conflicts by discarding local changes.

Updating the main openpilot base is a separate integration task. Review the
upstream changes and dependency pins together, resolve any dependency tree
replacements explicitly, and update the main manifest revision only after
integration. Never accept a gitlink in place of a source folder. Updater and CI
checks reject that layout.

Dependency provenance checks do not replace runtime, firmware, or vehicle
qualification for an update.
