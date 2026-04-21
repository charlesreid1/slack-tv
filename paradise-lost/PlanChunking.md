# Fix: Paradise Lost Book Headings Should Be Bold and Separate

## Context

Book headings in Paradise Lost (e.g., "Book I", "Book II") are posted as plain text lines, indistinguishable from poem lines. They should be visually distinct — posted as bold text in a separate Slack message before the poem lines that follow.

The current system posts 1 line at a time from `poem.txt` every 30 minutes using a deterministic time-based line index. It treats all lines identically, though it already detects book boundaries to select the bot username and icon. The 12 book headings appear at known positions in the text.

**The posting cadence (1 line every 30 minutes) stays the same.** The only change is that book heading lines get bold formatting.

## Approach

**Keep the existing 1-line-at-a-time posting. When the current line is a book heading, post it bold instead of plain.**

### Step 1: Identify book headings

The existing `BOOK_PATTERN` regex already matches book heading lines. No new data structure needed.

### Step 2: Update `post_line()` to bold book headings

In `post_line()`, after selecting the current line, check if it matches `BOOK_PATTERN`. If so, wrap it in Slack mrkdwn bold syntax (`*Book I*`) before sending. Otherwise, send as plain text (current behavior).

That's it. No changes to line indexing, timing, grouping, or cycle length.

### Files to modify

- `paradise-lost/notifier.py` — all changes are here

### Impact on timing

None. Same lines, same order, same 30-minute cadence. Book heading lines just render bold.

## Verification

1. Run `python notifier.py` locally (without env vars) to confirm it prints the expected output without crashing.
2. Temporarily set the line index to a known book heading position and verify:
   - A book heading line produces bold text (`*Book I*`)
   - A normal poem line is unchanged
3. Verify that the per-book icon/username selection still works correctly.
