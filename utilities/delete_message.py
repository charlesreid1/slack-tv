#!/usr/bin/env python3
"""Delete a single Slack message by its message URL.

Usage:
    python delete_message.py <message_url>              # dry run (default)
    python delete_message.py <message_url> --dry-run    # explicit dry run
    python delete_message.py <message_url> --real       # actually delete

Message URL format (copy from Slack via "Copy link"):
    https://yourworkspace.slack.com/archives/C012AB3CD/p1234567890123456

Environment:
    SLACK_BOT_TOKEN  — Bot User OAuth Token (xoxb-...)

Required Slack scopes:
    chat:write  — delete messages posted by this bot
"""

import os
import re
import sys
import requests


SLACK_DELETE_URL = "https://slack.com/api/chat.delete"


def parse_message_url(url):
    """Extract channel ID and message timestamp from a Slack message URL.

    Slack message URLs look like:
        https://workspace.slack.com/archives/C012AB3CD/p1234567890123456
        https://workspace.slack.com/archives/C012AB3CD/p1234567890123456?thread_ts=...

    The 'p' prefix on the timestamp is Slack's URL encoding — the actual ts
    is the digits with a dot inserted: p1234567890123456 -> 1234567890.123456
    """
    pattern = r"archives/([A-Z0-9]+)/p(\d{10})(\d{6})"
    match = re.search(pattern, url)
    if not match:
        return None, None
    channel_id = match.group(1)
    ts = f"{match.group(2)}.{match.group(3)}"
    return channel_id, ts


def delete_message(token, channel, ts):
    """Call chat.delete to remove a message."""
    response = requests.post(
        SLACK_DELETE_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={"channel": channel, "ts": ts},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack API error: {data.get('error')}")
    return data


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        sys.exit(0)

    url = sys.argv[1]
    flags = sys.argv[2:]

    real_mode = "--real" in flags
    # --dry-run is the default, but accept it explicitly too
    if "--dry-run" in flags and "--real" in flags:
        print("Error: --dry-run and --real are mutually exclusive.")
        sys.exit(1)

    channel_id, ts = parse_message_url(url)
    if not channel_id or not ts:
        print(f"Error: Could not parse message URL: {url}")
        print()
        print("Expected format:")
        print("  https://yourworkspace.slack.com/archives/C012AB3CD/p1234567890123456")
        sys.exit(1)

    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        print("Error: SLACK_BOT_TOKEN environment variable is not set.")
        sys.exit(1)

    print(f"Channel: {channel_id}")
    print(f"Message: {ts}")
    print()

    if not real_mode:
        print("[DRY RUN] Would delete message {ts} from channel {channel_id}.".format(
            ts=ts, channel_id=channel_id,
        ))
        print("Pass --real to actually delete.")
        return

    print(f"Deleting message {ts} from channel {channel_id}...")
    delete_message(token, channel_id, ts)
    print("Deleted.")


if __name__ == "__main__":
    main()
