import os
import requests
from datetime import datetime
import pytz

BOT_USERNAME = "Dactylic Odyssey"
BOT_ICON_URL = "https://raw.githubusercontent.com/charlesreid1/slack-tv/main/dactylic-odyssey/icon.png"

SLACK_API_URL = "https://slack.com/api/chat.postMessage"

LINES_PER_POST = 5
HOURS_PER_POST = 4


def load_poem_lines():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    poem_path = os.path.join(script_dir, "poem.txt")
    with open(poem_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f]
        return [line for line in lines if line]


LINES = load_poem_lines()
TOTAL_LINES = len(LINES)
TOTAL_CHUNKS = TOTAL_LINES // LINES_PER_POST


def get_current_chunk_index():
    """Deterministic chunk index: advances every HOURS_PER_POST hours since epoch."""
    now = datetime.utcnow()
    periods_since_epoch = int(now.timestamp()) // (3600 * HOURS_PER_POST)
    return periods_since_epoch % TOTAL_CHUNKS


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
    start = chunk_idx * LINES_PER_POST
    chunk_lines = LINES[start : start + LINES_PER_POST]
    text = "\n".join(chunk_lines)

    pacific_tz = pytz.timezone("America/Los_Angeles")
    now_pt = datetime.now(pacific_tz).strftime("%Y-%m-%d %H:%M PT")
    line_num = start + 1
    print(f"[{now_pt}] Posting chunk {chunk_idx + 1}/{TOTAL_CHUNKS} (lines {line_num}–{line_num + LINES_PER_POST - 1})")

    send_slack_message(token, channel, text)
    print(f"  Posted: {chunk_lines[0][:60]}")


if __name__ == "__main__":
    post_chunk()
