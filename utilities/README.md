# Utilities — Message Cleanup

Scripts for deleting messages posted by the Slack TV bot. Useful when testing a new channel, resetting after a bad deploy, or cleaning up a channel before archiving it.

Both scripts default to **dry-run mode** — they show what would happen without touching anything. Pass `--real` to actually delete.

---

## Before you start: expand the app's permissions

The channel notifiers only need `chat:write` and `chat:write.customize`. These utilities need two additional scopes so they can read channel history and identify bot messages.

### 1. Add the new scopes

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and select the **Slack TV** app
2. In the left sidebar, click **OAuth & Permissions**
3. Scroll to **Bot Token Scopes** and add:

| Scope | Why |
|-------|-----|
| `channels:history` | Read message history in public channels (`conversations.history`) |
| `groups:history` | Read message history in private channels (only needed if any Slack TV channel is private) |

The app should now have four (or five) scopes total:

| Scope | Used by |
|-------|---------|
| `chat:write` | notifiers (post messages) + utilities (delete messages) |
| `chat:write.customize` | notifiers (override bot name and icon per message) |
| `channels:history` | utilities (list messages in public channels) |
| `groups:history` | utilities (list messages in private channels) — optional |

### 2. Reinstall the app

After adding scopes, Slack requires you to reinstall:

1. Scroll to the top of the **OAuth & Permissions** page
2. Click **Reinstall to Workspace** → **Allow**
3. The **Bot User OAuth Token** (`xoxb-...`) stays the same — no secrets or config to update

That's it. The existing notifiers are unaffected; the new scopes are additive.

---

## Files

```
utilities/
├── delete_message.py       # Delete a single message by URL
├── clear_channel.py        # Delete all bot messages in a channel
├── requirements.txt        # Python dependencies
├── .environment.example    # Template — copy to .environment and fill in
├── .environment            # Your real tokens (git-ignored)
└── README.md
```

---

## Environment variables

These scripts are meant to be run locally on a developer's machine, not in CI. You need to set one variable:

| Variable | Value | Where to find it |
|----------|-------|-------------------|
| `SLACK_BOT_TOKEN` | `xoxb-...` | [api.slack.com/apps](https://api.slack.com/apps) → Slack TV → **OAuth & Permissions** → **Bot User OAuth Token** |

A `.environment.example` template is checked in. Copy it, fill in your token, and source it:

```bash
cp .environment.example .environment
# edit .environment — paste your real xoxb-... token
```

The real `.environment` file is git-ignored so tokens never get committed.

---

## Setup

```bash
cd utilities
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
source .environment
```

---

## delete_message.py

Delete a single message by its Slack URL. Get the URL by right-clicking a message in Slack → **Copy link**.

```bash
# Dry run (default) — shows what would be deleted
python delete_message.py "https://myworkspace.slack.com/archives/C012AB3CD/p1234567890123456"

# Actually delete
python delete_message.py "https://myworkspace.slack.com/archives/C012AB3CD/p1234567890123456" --real
```

The script parses the channel ID and message timestamp from the URL automatically. It can only delete messages posted by the bot (Slack enforces this — bots cannot delete other users' messages).

---

## clear_channel.py

Delete **all** messages posted by the bot in a given channel. Takes a channel ID, not a channel name.

```bash
# Dry run (default) — lists every bot message that would be deleted
python clear_channel.py C012AB3CD

# Actually delete (prompts for confirmation)
python clear_channel.py C012AB3CD --real

# Actually delete (skip confirmation prompt)
python clear_channel.py C012AB3CD --real --force
```

### How it works

1. Calls `auth.test` to learn the bot's own user ID
2. Pages through `conversations.history` to find all messages in the channel
3. Filters to messages where `user` matches the bot's user ID
4. In dry-run mode, prints the list and stops
5. In real mode, deletes each message via `chat.delete` with a 1.2-second delay between calls to stay within Slack's rate limits (~50 requests/minute for Tier 3 methods)

### Safety rails

- **Dry run by default** — you have to explicitly opt in with `--real`
- **Confirmation prompt** — in `--real` mode, prints a loud warning and requires typing `y` before proceeding
- **`--force` flag** — skips the confirmation prompt for scripted use, but still requires `--real`
- **Bot messages only** — the script identifies and deletes only messages posted by the bot token you're using; other users' messages are untouched

---

## Finding the channel ID

Slack's API uses channel IDs, not names. To find a channel's ID:

- Open Slack in a browser, navigate to the channel, and grab the ID from the URL:
  ```
  https://app.slack.com/client/T.../C012AB3CD
                                     ^^^^^^^^^^^ channel ID
  ```
- Or: right-click the channel name → **View channel details** → scroll to the bottom of the **About** tab
