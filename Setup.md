# Repository Setup Guide

This document covers the one-time GitHub and Slack setup required before any channel will run.

---

## How it works

Slack TV is a collection of bots that post scheduled content into Slack channels. Each channel has its own subdirectory with a `notifier.py` that defines what to post and how the bot appears.

All channels share a **single Slack app** with a single **Bot Token** (`SLACK_BOT_TOKEN`). Each channel's `notifier.py` sets its own `BOT_USERNAME` and `BOT_ICON_URL`, which are passed to the `chat.postMessage` API — so each channel appears as a different user even though the same app is doing it.

This requires the `chat:write.customize` OAuth scope.

---

## 1. Create the Slack App (one-time)

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**
2. Name it (e.g., "Slack TV") and select your workspace
3. In the left sidebar, click **Basic Information**
4. Under **Display Information**, set the app name and description — this is just the fallback identity; each channel overrides the name and icon per message
5. In the left sidebar, click **OAuth & Permissions**
6. Under **Bot Token Scopes**, add:
   - `chat:write` — post messages
   - `chat:write.customize` — override username and icon per message
7. Scroll up and click **Install to Workspace**, then **Allow**
8. Copy the **Bot User OAuth Token** — it looks like `xoxb-...`

---

## 2. Add the Bot Token to GitHub

Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.

| Secret name | Value |
|-------------|-------|
| `SLACK_BOT_TOKEN` | `xoxb-...` token from step 1 |

This is added once and shared by all channels.

---

## 3. Create a Slack channel and invite the bot

1. Create the Slack channel (e.g., `#waste-land`)
2. Open the channel → click the channel name at the top → **Integrations** tab → **Add an App** → find your app and add it

---

## 4. Get the Channel ID

Slack's API requires a channel ID, not the channel name.

Open Slack in a browser, navigate to the channel, and copy the ID from the URL:
```
https://app.slack.com/client/T.../C012AB3CD
                                   ^^^^^^^^^^^ channel ID
```

Or: right-click the channel name → **View channel details** → scroll to the bottom of the **About** tab.

---

## 5. Add the Channel ID to GitHub secrets

Add a GitHub Actions secret for each channel. The secret name follows the pattern `<CHANNEL_NAME>_CHANNEL_ID` in `SCREAMING_SNAKE_CASE`.

| Secret name | Value |
|-------------|-------|
| `WASTE_LAND_CHANNEL_ID` | channel ID from step 4 |

### Channel registry

| Channel | Subdirectory | GitHub secret |
|---------|-------------|---------------|
| The Waste Land | `waste-land/` | `WASTE_LAND_CHANNEL_ID` |

Add a row here as you add new channels.

---

## 6. Set the per-channel identity in code

Each channel's `notifier.py` has these two lines at the top:

```python
BOT_USERNAME = "The Waste Land"
BOT_ICON_URL = "https://raw.githubusercontent.com/<owner>/slack-tv/main/waste-land/icon.png"
```

`BOT_USERNAME` is the display name that will appear in Slack for that channel's posts.

`BOT_ICON_URL` sets the avatar. Each channel keeps its icon image (e.g., `icon.png`) in its own subdirectory. Since this repo is public, the image is served directly via GitHub's raw URL:

```
https://raw.githubusercontent.com/<owner>/slack-tv/main/<channel-dir>/icon.png
```

This keeps icons version-controlled alongside the code — no separate hosting needed.

---

## 7. Verify the scheduled run

1. Go to the **Actions** tab in your GitHub repository
2. Select the channel's action (e.g., **The Waste Land**)
3. Click **Run workflow** → **Run workflow**
4. Check the logs and verify the post appeared in Slack under the correct name and icon

---

## Adding a new channel

1. Create a new subdirectory (e.g., `divine-comedy/`)
2. Add `notifier.py`, `requirements.txt`, and an `icon.png`
3. Set `BOT_USERNAME` and `BOT_ICON_URL` in `notifier.py` (use the raw GitHub URL for the icon)
4. Copy `.github/workflows/waste-land.yml` to `.github/workflows/divine-comedy.yml`
5. Update the action: `name`, `cron` schedule, and `SLACK_CHANNEL_ID` secret name
6. Create the Slack channel and invite the bot (step 3)
7. Get the channel ID and add it as a GitHub secret (steps 4–5)
8. Add the row to the channel registry table above
9. Trigger the action manually to test

---

## Naming conventions

- **Subdirectory**: kebab-case (e.g., `waste-land`, `divine-comedy`)
- **Action file**: same as subdirectory + `.yml` (e.g., `waste-land.yml`)
- **Channel ID secret**: `SCREAMING_SNAKE_CASE` + `_CHANNEL_ID` (e.g., `DIVINE_COMEDY_CHANNEL_ID`)
- **Bot icon**: `icon.png` in the channel's subdirectory

---

## Cron schedule reference

GitHub Actions cron runs in UTC. Schedules may fire up to ~15 minutes late during high-load periods — scripts should be idempotent. The epoch-based index in `waste-land/notifier.py` handles this automatically.

| Description | Cron expression |
|-------------|----------------|
| Every hour | `0 * * * *` |
| Every 4 hours | `0 */4 * * *` |
| Daily at 9 AM PT (17:00 UTC) | `0 17 * * *` |
| Daily at midnight PT (8:00 UTC) | `0 8 * * *` |
| Weekdays at noon PT (20:00 UTC) | `0 20 * * 1-5` |
