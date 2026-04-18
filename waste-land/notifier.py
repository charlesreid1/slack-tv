import os
import requests
from datetime import datetime
import pytz

BOT_USERNAME = "The Waste Land"
BOT_ICON_URL = "https://raw.githubusercontent.com/charlesreid1/slack-tv/main/waste-land/icon.png"

SLACK_API_URL = "https://slack.com/api/chat.postMessage"

# The Waste Land by T.S. Eliot (1922) — public domain
# 434 lines. At one line per hour, the poem loops every ~18 days.
def load_poem_lines():
    """Load poem from poem.txt, strip whitespace, discard empty lines."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    poem_path = os.path.join(script_dir, "poem.txt")
    with open(poem_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f]
        return [line for line in lines if line]

LINES = load_poem_lines()

TOTAL_LINES = len(LINES)


def get_current_line_index():
    """Determine which line to post based on hours elapsed since epoch."""
    now = datetime.utcnow()
    hours_since_epoch = int(now.timestamp()) // 3600
    return hours_since_epoch % TOTAL_LINES


def send_slack_message(token, channel, text, thread_ts=None):
    payload = {
        "channel": channel,
        "text": text,
        "username": BOT_USERNAME,
        "icon_url": BOT_ICON_URL,
    }
    if thread_ts:
        payload["thread_ts"] = thread_ts
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


def post_line():
    token = os.getenv("SLACK_BOT_TOKEN")
    channel = os.getenv("SLACK_CHANNEL_ID")

    if not token or not channel:
        print("SLACK_BOT_TOKEN and SLACK_CHANNEL_ID must be set. Skipping.")
        return

    idx = get_current_line_index()
    line_text = LINES[idx]

    pacific_tz = pytz.timezone("America/Los_Angeles")
    now_pt = datetime.now(pacific_tz).strftime("%Y-%m-%d %H:%M PT")
    print(f"[{now_pt}] Posting line {idx + 1}/{TOTAL_LINES}")

    send_slack_message(token, channel, line_text)
    print(f"  Posted: {line_text[:60]}")


if __name__ == "__main__":
    post_line()
