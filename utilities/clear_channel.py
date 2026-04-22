#!/usr/bin/env python3
"""Delete ALL messages posted by this bot in a Slack channel.

Usage:
    python clear_channel.py <channel_id>                # dry run (default)
    python clear_channel.py <channel_id> --dry-run      # explicit dry run
    python clear_channel.py <channel_id> --real          # actually delete (prompts for confirmation)
    python clear_channel.py <channel_id> --real --force  # actually delete (skip confirmation)

Environment:
    SLACK_BOT_TOKEN  — Bot User OAuth Token (xoxb-...)

Required Slack scopes:
    channels:history  — read message history in public channels
    groups:history    — read message history in private channels (if needed)
    chat:write        — delete messages posted by this bot
"""

import os
import sys
import time
import requests


SLACK_HISTORY_URL = "https://slack.com/api/conversations.history"
SLACK_DELETE_URL = "https://slack.com/api/chat.delete"
SLACK_AUTH_TEST_URL = "https://slack.com/api/auth.test"


def get_bot_user_id(token):
    """Get the bot's own user ID via auth.test."""
    response = requests.post(
        SLACK_AUTH_TEST_URL,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack API error: {data.get('error')}")
    return data["user_id"]


def fetch_bot_messages(token, channel, bot_user_id):
    """Fetch all messages in a channel posted by the bot.

    Pages through conversations.history (newest-first, 200 per page) and
    collects messages where the user field matches the bot's user ID.
    """
    messages = []
    cursor = None

    while True:
        params = {"channel": channel, "limit": 200}
        if cursor:
            params["cursor"] = cursor

        response = requests.get(
            SLACK_HISTORY_URL,
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("ok"):
            raise RuntimeError(f"Slack API error: {data.get('error')}")

        for msg in data.get("messages", []):
            if msg.get("user") == bot_user_id:
                messages.append(msg)

        # Pagination
        metadata = data.get("response_metadata", {})
        cursor = metadata.get("next_cursor")
        if not cursor:
            break

    return messages


def delete_message(token, channel, ts):
    """Call chat.delete to remove a message. Returns True on success."""
    response = requests.post(
        SLACK_DELETE_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={"channel": channel, "ts": ts},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        error = data.get("error")
        if error == "message_not_found":
            # Already deleted or ephemeral — not a failure
            return False
        raise RuntimeError(f"Slack API error: {error}")
    return True


def confirm_destructive_action(channel, count):
    """Print a loud warning and require 'y' + Enter to proceed."""
    print()
    print("=" * 60)
    print("  WARNING: DESTRUCTIVE ACTION")
    print("=" * 60)
    print()
    print(f"  You are about to permanently delete {count} message(s)")
    print(f"  from channel {channel}.")
    print()
    print("  This CANNOT be undone.")
    print()
    print("=" * 60)
    print()
    answer = input("  Type 'y' and press Enter to continue: ")
    return answer.strip().lower() == "y"


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        sys.exit(0)

    channel = sys.argv[1]
    flags = sys.argv[2:]

    real_mode = "--real" in flags
    force = "--force" in flags

    if "--dry-run" in flags and "--real" in flags:
        print("Error: --dry-run and --real are mutually exclusive.")
        sys.exit(1)

    if force and not real_mode:
        print("Error: --force only makes sense with --real.")
        sys.exit(1)

    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        print("Error: SLACK_BOT_TOKEN environment variable is not set.")
        sys.exit(1)

    # Identify who we are
    print("Identifying bot user...")
    bot_user_id = get_bot_user_id(token)
    print(f"Bot user ID: {bot_user_id}")
    print()

    # Fetch messages
    print(f"Fetching messages from channel {channel}...")
    bot_messages = fetch_bot_messages(token, channel, bot_user_id)
    print(f"Found {len(bot_messages)} message(s) from this bot.")

    if not bot_messages:
        print("Nothing to delete.")
        return

    # Show preview
    print()
    print("Messages to delete:")
    print("-" * 60)
    for msg in bot_messages:
        ts = msg["ts"]
        text = msg.get("text", "")
        preview = text[:70].replace("\n", " ")
        if len(text) > 70:
            preview += "..."
        print(f"  [{ts}] {preview}")
    print("-" * 60)
    print()

    if not real_mode:
        print(f"[DRY RUN] Would delete {len(bot_messages)} message(s) from channel {channel}.")
        print("Pass --real to actually delete.")
        return

    # Confirmation gate
    if not force:
        if not confirm_destructive_action(channel, len(bot_messages)):
            print("Aborted.")
            sys.exit(0)

    # Delete
    deleted = 0
    skipped = 0
    for i, msg in enumerate(bot_messages, 1):
        ts = msg["ts"]
        text_preview = msg.get("text", "")[:50].replace("\n", " ")
        sys.stdout.write(f"\r  Deleting {i}/{len(bot_messages)}: [{ts}] {text_preview}")
        sys.stdout.flush()
        if delete_message(token, channel, ts):
            deleted += 1
        else:
            skipped += 1
        # Slack rate limit: ~50 requests per minute for chat.delete (Tier 3)
        # Sleep briefly between deletions to stay well within limits.
        time.sleep(1.2)

    print()
    print()
    print(f"Done. Deleted {deleted}, skipped {skipped} (already gone).")


if __name__ == "__main__":
    main()
