# Retained presentation assets

`fonts` contains the unchanged four Inter bitmap pairs and one Unifont bitmap
pair used by the presentation reference, plus the supplied Sora wordmark font
and its weight-800 bitmap pair. `font-sources.json` records the retained files'
hash, original source font, notices and retained bitmap source. Subsetting and
bitmap generation do not make these fonts MIT or newly authored by StarPilot.

Inter's source metadata identifies version 3.012, build `git-06b166889`, and
SIL Open Font License 1.1. Its versioned license and each source font's embedded
2020 copyright record are retained under `fonts/notices`. The source TTFs match
the pinned official openpilot assets. The publisher's Windows-hinted v3.12
release TTFs differ; the exact earlier build/export step is not established.

Unifont's source OTF matches the publisher's 17.0.02 archive exactly. Its full
copyright, OFL text and COPYING document retain the dual-license explanation:
OFL 1.1 or GPL version 2 or later with the GNU Font Embedding Exception. COPYING
also describes other files in the publisher's source distribution; this package
contains only the existing bitmap font pair.

The original bitmap-generation environment has not been reconstructed. The
current recipe's glyph lists differ from the stored atlases, so these exact files
are preserved without regeneration. They are not full language-coverage fonts.

`notices/Bootstrap-MIT.txt` preserves the pinned 2019–2021 Bootstrap Authors
notice for the existing backspace icon. That icon is reused from the official
asset tree, with no binary copy here. `notices/Material-Design-Apache-2.0.txt`
preserves the existing attribution to modified Google Material Design Icons;
this umbrella attribution does not identify every image's artistic source.
The adjacent UI code license and root project license remain applicable to their
respective code; they do not replace the font and image notices.

Como is no longer required by the Home brand role. The eGPU and Bluetooth icons
are bundled under `selfdrive/assets` and pinned in `home-assets.json`; their
specific artistic source records remain a separate provenance question.
The Home brand role now uses the
source-owned Sora bitmap, generated from the supplied `Sora[wght].ttf` at the
font's maximum `wght=800`; it does not have a width axis. The generated pair is
pinned in `sora-brand-font.json` and retains Sora's embedded copyright and SIL
Open Font License notice. Home can now use the pinned source-owned Sora, Inter,
and Unifont fonts without an external directory. An explicit font-directory
override remains available and must pass the same byte validation.
