# Fix: Odyssey Chapter Titles Should Be Bold and Separate

## Context

Chapter/section titles in the Odyssey (e.g., "Athena Inspires the Prince", "Telemachus Sets Sail") are posted as plain text, making them indistinguishable from poem lines. They should be visually distinct — posted as bold text in a separate Slack message before the poem lines that follow.

The current system posts 5 lines at a time from `poem.txt` using a deterministic time-based chunk index. It treats all lines identically. The 24 chapter titles appear at known line numbers in the text.

## Approach

**Stop treating lines as a flat list. Instead, build chapter-aware chunking.**

### Step 1: Define the 24 chapter titles

Add a hardcoded set of the 24 chapter title strings to `notifier.py`. These are the exact lines from `poem.txt`:

```
"Athena Inspires the Prince"        (line 1)
"Telemachus Sets Sail"              (line 536)
"King Nestor Remembers"             (line 1030)
"The King and Queen of Sparta"      (line 1604)
"Odysseus —Nymph and Shipwreck"     (line 2583)
"The Princess and the Stranger"     (line 3142)
"Phaeacia's Halls and Gardens"      (line 3519)
"A Day for Songs and Contests"      (line 3926)
"In the One-Eyed Giant's Cave"      (line 4604)
"The Bewitching Queen of Aeaea"     (line 5254)
"The Kingdom of the Dead"           (line 5898)
"The Cattle of the Sun"             (line 6648)
"Ithaca at Last"                    (line 7147)
"The Loyal Swineherd"               (line 7664)
"The Prince Sets Sail for Home"     (line 8282)
"Father and Son"                    (line 8918)
"Stranger at the Gates"             (line 9464)
"The Beggar-King of Ithaca"         (line 10162)
"Penelope and Her Guest"            (line 10664)
"Portents Gather"                   (line 11371)
"Odysseus Strings His Bow"          (line 11831)
"Slaughter in the Hall"             (line 12336)
"The Great Rooted Bed"              (line 12883)
"Peace"                             (line 13319)
```

### Step 2: Build structured content blocks instead of flat chunks

Replace the current flat chunking with a two-pass approach:

1. **When loading lines**, build a list of "content blocks" where each block is either:
   - `("title", "Athena Inspires the Prince")` — a chapter title
   - `("lines", ["line1", "line2", ..., "line5"])` — a group of up to 5 poem lines

2. **Splitting logic**: Walk through all lines. When a line matches a chapter title, emit it as a title block. Accumulate non-title lines into groups of 5, emitting a lines block each time 5 are collected. When a title is encountered mid-accumulation, flush the partial group (even if < 5 lines) as its own block, then emit the title block. This is the "aesthetically clean" approach — a chapter ending with 2 remaining lines gets posted as just those 2 lines, then the title appears next.

3. **`TOTAL_CHUNKS`** becomes `len(content_blocks)` instead of `TOTAL_LINES // 5`.

### Step 3: Update `post_chunk()` to handle both block types

- For a `"title"` block: send a single message with the title in bold (`*Title Text*` — Slack mrkdwn bold syntax).
- For a `"lines"` block: send as before, newline-joined plain text.

### Files to modify

- `dactylic-odyssey/notifier.py` — all changes are here

### Impact on timing

The total number of chunks will increase slightly (by ~24 for the title blocks, plus some extra partial-line blocks at chapter boundaries). This means the full cycle time increases, but the hourly posting cadence stays the same. The anchor time doesn't change.

## Verification

1. Run `python notifier.py` locally (without env vars) to confirm it prints the expected chunk info without crashing.
2. Add a small test/debug mode: temporarily set chunk index to known title-boundary chunks and verify:
   - A title block produces bold text (`*Title*`)
   - A partial block at a chapter end has < 5 lines
   - A normal block has exactly 5 lines
3. Inspect the first ~10 content blocks to confirm the sequence: title block → 5-line blocks → partial block → title block → ...
