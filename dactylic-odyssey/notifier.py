import os
import requests
from datetime import datetime
import pytz

BOT_USERNAME = "Dactylic Odyssey"
BOT_ICON_URL = "https://git.charlesreid1.com/charlesreid1/slack-tv/raw/branch/main/dactylic-odyssey/icon.png"

SLACK_API_URL = "https://slack.com/api/chat.postMessage"

LINES_PER_POST = 5
HOURS_PER_POST = 1

# Chapter titles from poem.txt (exact lines)
CHAPTER_TITLES = [
    "Athena Inspires the Prince",        # line 1
    "Telemachus Sets Sail",              # line 536
    "King Nestor Remembers",             # line 1030
    "The King and Queen of Sparta",      # line 1604
    "Odysseus —Nymph and Shipwreck",     # line 2583
    "The Princess and the Stranger",     # line 3142
    "Phaeacia’s Halls and Gardens",      # line 3519
    "A Day for Songs and Contests",      # line 3926
    "In the One-Eyed Giant’s Cave",      # line 4604
    "The Bewitching Queen of Aeaea",     # line 5254
    "The Kingdom of the Dead",           # line 5898
    "The Cattle of the Sun",             # line 6648
    "Ithaca at Last",                    # line 7147
    "The Loyal Swineherd",               # line 7664
    "The Prince Sets Sail for Home",     # line 8282
    "Father and Son",                    # line 8918
    "Stranger at the Gates",             # line 9464
    "The Beggar-King of Ithaca",         # line 10162
    "Penelope and Her Guest",            # line 10664
    "Portents Gather",                   # line 11371
    "Odysseus Strings His Bow",          # line 11831
    "Slaughter in the Hall",             # line 12336
    "The Great Rooted Bed",              # line 12883
    "Peace",                             # line 13319
]


def load_poem_lines():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    poem_path = os.path.join(script_dir, "poem.txt")
    with open(poem_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f]
        return [line for line in lines if line]


def build_content_blocks():
    """Build structured content blocks from poem lines.

    Returns a list where each element is either:
    - ("title", "Chapter Title") for chapter titles
    - ("lines", ["line1", "line2", ..., "lineN"]) for poem lines (N ≤ LINES_PER_POST)
    """
    lines = load_poem_lines()
    blocks = []
    current_lines = []

    for line in lines:
        if line in CHAPTER_TITLES:
            # Flush any accumulated poem lines before the title
            if current_lines:
                blocks.append(("lines", current_lines.copy()))
                current_lines = []
            # Add the title as its own block
            blocks.append(("title", line))
        else:
            # Accumulate poem lines
            current_lines.append(line)
            # Flush when we have LINES_PER_POST lines
            if len(current_lines) == LINES_PER_POST:
                blocks.append(("lines", current_lines.copy()))
                current_lines = []

    # Flush any remaining poem lines at the end
    if current_lines:
        blocks.append(("lines", current_lines.copy()))

    return blocks


CONTENT_BLOCKS = build_content_blocks()
TOTAL_CHUNKS = len(CONTENT_BLOCKS)


def get_current_chunk_index():
    """Deterministic chunk index: advances every HOURS_PER_POST hours since 10:00 AM Pacific on 2026-04-20."""
    pacific_tz = pytz.timezone("America/Los_Angeles")
    anchor = pacific_tz.localize(datetime(2026, 4, 20, 10, 0, 0))
    now = datetime.now(pacific_tz)
    elapsed_seconds = (now - anchor).total_seconds()
    periods_since_anchor = max(0, int(elapsed_seconds)) // (3600 * HOURS_PER_POST)
    return periods_since_anchor % TOTAL_CHUNKS


def send_slack_message(token, channel, text):
    payload = {
        "channel": channel,
        "text": text,
        "username": BOT_USERNAME,
        "icon_url": BOT_ICON_URL,
    }
    response = requests.post(
        SLACK_API_URL,
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack API error: {data.get('error')}")
    return data


def post_chunk():
    token = os.getenv("SLACK_BOT_TOKEN")
    channel = os.getenv("SLACK_CHANNEL_ID")

    if not token or not channel:
        print("SLACK_BOT_TOKEN and SLACK_CHANNEL_ID must be set. Skipping.")
        return

    chunk_idx = get_current_chunk_index()
    block_type, block_content = CONTENT_BLOCKS[chunk_idx]

    pacific_tz = pytz.timezone("America/Los_Angeles")
    now_pt = datetime.now(pacific_tz).strftime("%Y-%m-%d %H:%M PT")

    if block_type == "title":
        # Chapter title: send as bold text
        text = f"*{block_content}*"
        print(f"[{now_pt}] Posting chunk {chunk_idx + 1}/{TOTAL_CHUNKS} (chapter title)")
        send_slack_message(token, channel, text)
        print(f"  Posted: *{block_content}*")
    else:
        # Poem lines: send as plain text
        text = "\n".join(block_content)
        line_count = len(block_content)
        print(f"[{now_pt}] Posting chunk {chunk_idx + 1}/{TOTAL_CHUNKS} ({line_count} line{'s' if line_count != 1 else ''})")
        send_slack_message(token, channel, text)
        print(f"  Posted: {block_content[0][:60]}")


def debug_content_blocks(limit=20, start=0):
    """Print N content blocks for debugging."""
    print(f"Total chunks (content blocks): {TOTAL_CHUNKS}")
    print(f"Content blocks {start} to {start + limit - 1}:")
    print("-" * 60)
    for i, (block_type, content) in enumerate(CONTENT_BLOCKS[start:start + limit]):
        idx = start + i
        if block_type == "title":
            print(f"{idx:3d}: TITLE -> *{content}*")
        else:
            line_count = len(content)
            preview = content[0][:40] + "..." if len(content[0]) > 40 else content[0]
            print(f"{idx:3d}: LINES ({line_count}) -> {preview}")


if __name__ == "__main__":
    post_chunk()
