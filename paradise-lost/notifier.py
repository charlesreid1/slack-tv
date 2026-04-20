import os
import re
import requests
from datetime import datetime
import pytz

ICON_URL_BASE = "https://git.charlesreid1.com/charlesreid1/slack-tv/raw/branch/main/paradise-lost"

SLACK_API_URL = "https://slack.com/api/chat.postMessage"

BOOK_PATTERN = re.compile(r"^Book\s+(I{1,3}|IV|V|VI{0,3}|IX|X|XI{0,2})$")

ROMAN_TO_INT = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6,
    "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12,
}


def load_poem():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    poem_path = os.path.join(script_dir, "poem.txt")
    with open(poem_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f]
        return [line for line in lines if line]


LINES = load_poem()
TOTAL_LINES = len(LINES)


def get_current_line_index():
    now = datetime.utcnow()
    hours_since_epoch = int(now.timestamp()) // 3600
    return hours_since_epoch % TOTAL_LINES


def get_book_for_line(lines, idx):
    for i in range(idx, -1, -1):
        m = BOOK_PATTERN.match(lines[i])
        if m:
            roman = m.group(1)
            return ROMAN_TO_INT[roman]
    return 1


def send_slack_message(token, channel, text, username, icon_url):
    payload = {
        "channel": channel,
        "text": text,
        "username": username,
        "icon_url": icon_url,
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


def post_line():
    token = os.getenv("SLACK_BOT_TOKEN")
    channel = os.getenv("SLACK_CHANNEL_ID")

    if not token or not channel:
        print("SLACK_BOT_TOKEN and SLACK_CHANNEL_ID must be set. Skipping.")
        return

    idx = get_current_line_index()
    line_text = LINES[idx]

    book_num = get_book_for_line(LINES, idx)
    roman = {v: k for k, v in ROMAN_TO_INT.items()}[book_num]
    username = f"Paradise Lost Book {roman}"
    icon_url = f"{ICON_URL_BASE}/icon{book_num:02d}.png"

    pacific_tz = pytz.timezone("America/Los_Angeles")
    now_pt = datetime.now(pacific_tz).strftime("%Y-%m-%d %H:%M PT")
    print(f"[{now_pt}] Posting line {idx + 1}/{TOTAL_LINES} (Book {roman})")

    send_slack_message(token, channel, line_text, username, icon_url)
    print(f"  Posted: {line_text[:60]}")


if __name__ == "__main__":
    post_line()
