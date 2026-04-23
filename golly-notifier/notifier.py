import os
import sys
import re
import requests
from datetime import datetime
import pytz

SLACK_API_URL = "https://slack.com/api/chat.postMessage"

CUPS = {
    "star": {
        "api_base": "https://cloud.star.vii.golly.life",
        "site_base": "https://star.vii.golly.life",
        "cup_name": "Star Cup",
        "cup_series_key": "SCS",
        "bot_username": "Star Cup",
        "bot_icon_url": "https://git.charlesreid1.com/charlesreid1/slack-tv/raw/branch/main/golly-notifier/star-cup-icon.png",
        # weekday(): 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
        "schedule": {
            1: {"start_hour": 5, "duration": 20},  # Tuesday: LDS+LCS, 5 AM for 20h
            2: {"start_hour": 5, "duration": 12},  # Wednesday: Cup Series, 5 AM for 12h
        },
    },
    "hellmouth": {
        "api_base": "https://cloud.vii.golly.life",
        "site_base": "https://vii.golly.life",
        "cup_name": "Hellmouth Cup",
        "cup_series_key": "HCS",
        "bot_username": "Hellmouth Cup",
        "bot_icon_url": "https://git.charlesreid1.com/charlesreid1/slack-tv/raw/branch/main/golly-notifier/hellmouth-cup-icon.png",
        # weekday(): 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
        "schedule": {
            4: {"start_hour": 8, "duration": 8},   # Friday: LDS, 8 AM for 8h
            5: {"start_hour": 8, "duration": 12},  # Saturday: LCS, 8 AM for 12h
            6: {"start_hour": 8, "duration": 12},  # Sunday: Cup Series, 8 AM for 12h
        },
    },
}

SERIES_NAMES = {
    "LDS": "Division Series",
    "LCS": "Championship Series",
    "HCS": "Hellmouth VII Cup",
    "SCS": "Star VII Cup",
}

MODE_TO_SERIES = {
    31: "LDS",
    32: "LCS",
    33: None,  # filled per-cup: HCS or SCS
}


# ---------------------------------------------------------------------------
# Slack helpers
# ---------------------------------------------------------------------------

def fetch_json(url):
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def send_slack_message(token, channel, text, username, icon_url, attachments=None):
    payload = {
        "channel": channel,
        "text": text,
        "username": username,
        "icon_url": icon_url,
    }
    if attachments:
        payload["attachments"] = attachments
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


def game_link(site_base, game):
    game_id = game.get("id", "")
    desc = game.get("description", "")
    match = re.match(r"Game (\d+)", desc)
    label = f"Game {match.group(1)}" if match else "Watch"
    url = f"{site_base}/simulator/index.html?gameId={game_id}"
    return f"<{url}|{label}>"


def game_link_url(site_base, game):
    game_id = game.get("id", "")
    return f"{site_base}/simulator/index.html?gameId={game_id}"


def game_link_label(game):
    desc = game.get("description", "")
    match = re.match(r"Game (\d+)", desc)
    return f"Game {match.group(1)}" if match else "View Simulation"


# ---------------------------------------------------------------------------
# Block Kit card builders (mimic vii.golly.life game card style)
#
# Design reference (from the site's HTML/CSS):
#   - Dark card background (#272b30, Bootswatch Slate)
#   - Team 1 name + (W-L) record, score right-aligned
#   - Team 2 name + (W-L) record, score right-aligned
#   - Winner is bold, loser is normal weight
#   - Map name + generation count below
#   - Green "View Simulation" button (#62c462)
#   - Sidebar color = winning team's color
#
# Slack constraints:
#   - No colored text in Block Kit, so we use *bold* for the winner
#   - Colored sidebar via attachment "color" field
#   - Section blocks with fields for the two-column team/score layout
# ---------------------------------------------------------------------------

def _finished_game_attachment(g, site_base=None):
    """Build a Slack attachment with Block Kit blocks for a finished game.

    Mirrors the vii.golly.life finished-game-card layout:
      Team 1 Name (W-L)        score
      Team 2 Name (W-L)        score
      Map: <map name>
      <generations> Generations
      [View Simulation]
    """
    t1_score = g.get("team1Score", 0)
    t2_score = g.get("team2Score", 0)
    t1_color = g.get("team1Color", "#aaaaaa")
    t2_color = g.get("team2Color", "#aaaaaa")

    # Determine winner for bold styling and sidebar color
    if t1_score > t2_score:
        winner_color = t1_color
        t1_fmt = "*{name}*"
        t2_fmt = "{name}"
    else:
        winner_color = t2_color
        t1_fmt = "{name}"
        t2_fmt = "*{name}*"

    # Series win-loss records (pre-game, as shown on the card)
    w1, l1 = g.get("team1SeriesWinLoss", [0, 0])
    w2, l2 = g.get("team2SeriesWinLoss", [0, 0])
    t1_record = f" ({w1}-{l1})" if w1 or l1 else ""
    t2_record = f" ({w2}-{l2})" if w2 or l2 else ""

    t1_label = t1_fmt.format(name=g["team1Name"]) + t1_record
    t2_label = t2_fmt.format(name=g["team2Name"]) + t2_record

    map_name = g.get("mapName", "Unknown")
    generations = g.get("generations", 0)

    blocks = [
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": t1_label},
                {"type": "mrkdwn", "text": f"*{t1_score}*" if t1_score > t2_score else str(t1_score)},
            ],
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": t2_label},
                {"type": "mrkdwn", "text": f"*{t2_score}*" if t2_score > t1_score else str(t2_score)},
            ],
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Map: {map_name}"},
                {"type": "mrkdwn", "text": f"{generations} Generations"},
            ],
        },
    ]

    if site_base:
        url = game_link_url(site_base, g)
        label = "View Simulation"
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": label},
                    "url": url,
                    "style": "primary",
                },
            ],
        })

    # Plain text fallback for notifications / non-Block-Kit clients
    fallback = (
        f"{g['team1Name']} {t1_score} - {g['team2Name']} {t2_score} "
        f"| Map: {map_name} | {generations} Gen"
    )

    return {
        "color": winner_color,
        "blocks": blocks,
        "fallback": fallback,
    }


def _upcoming_game_attachment(g, site_base=None):
    """Build a Slack attachment for an upcoming/in-progress game (no scores yet).

    Mirrors the vii.golly.life scheduled/in-progress game card:
      Team 1 Name (W-L)
      Team 2 Name (W-L)
      Map: <map name>
      [View Simulation]
    """
    w1, l1 = g.get("team1SeriesWinLoss", [0, 0])
    w2, l2 = g.get("team2SeriesWinLoss", [0, 0])
    t1_record = f" ({w1}-{l1})" if w1 or l1 else ""
    t2_record = f" ({w2}-{l2})" if w2 or l2 else ""

    t1_label = g["team1Name"] + t1_record
    t2_label = g["team2Name"] + t2_record

    map_name = g.get("mapName", "Unknown")

    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{t1_label}*\n*{t2_label}*"},
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Map: {map_name}"},
            ],
        },
    ]

    if site_base:
        url = game_link_url(site_base, g)
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Simulation"},
                    "url": url,
                    "style": "primary",
                },
            ],
        })

    fallback = f"{g['team1Name']} vs. {g['team2Name']} | Map: {map_name}"

    # Use team1's color for the sidebar on upcoming games
    sidebar_color = g.get("team1Color", "#3a3f44")

    return {
        "color": sidebar_color,
        "blocks": blocks,
        "fallback": fallback,
    }


def _header_attachment(header_text):
    """Simple styled header as an attachment (for series titles, day headers)."""
    return {
        "color": "#3a3f44",
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{header_text}*"},
            },
        ],
        "fallback": header_text,
    }


def _series_clinch_attachment(winner, winner_wl, loser, loser_wl, winner_color):
    """Styled announcement that a team has won the series."""
    text = f"*{winner}* ({winner_wl}) wins the series over {loser} ({loser_wl})"
    return {
        "color": winner_color,
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text},
            },
        ],
        "fallback": f"{winner} ({winner_wl}) wins the series over {loser} ({loser_wl})",
    }


# ---------------------------------------------------------------------------
# Notification builders
#
# Each returns a list of message dicts: {"text": str, "attachments": list}
# A single Slack API call sends one message dict.
# ---------------------------------------------------------------------------

def format_matchup(g, site_base=None):
    """Build a single attachment for a finished game result."""
    return _finished_game_attachment(g, site_base)


def format_current_games(current_games, site_base=None):
    """Build a list of attachments for today's upcoming/in-progress games."""
    attachments = []
    for g in sorted(current_games, key=lambda x: x.get("description", "")):
        attachments.append(_upcoming_game_attachment(g, site_base))
    return attachments


def updated_series_wl(game):
    """Return (team1_wins, team1_losses, team2_wins, team2_losses) accounting for this game's outcome."""
    w1, l1 = game["team1SeriesWinLoss"]
    w2, l2 = game["team2SeriesWinLoss"]
    if game["team1Score"] > game["team2Score"]:
        w1 += 1
        l2 += 1
    else:
        w2 += 1
        l1 += 1
    return w1, l1, w2, l2


def build_notification(cup_config, mode_data, postseason, current_games=None):
    """Build styled Slack messages for the current game state.

    Returns a list of message dicts, each with:
      - "text": plain-text fallback
      - "attachments": list of Slack attachments with Block Kit blocks
    """
    mode = mode_data["mode"]
    elapsed = mode_data.get("elapsed", 0)
    cup_name = cup_config["cup_name"]
    cup_series_key = cup_config["cup_series_key"]
    site_base = cup_config.get("site_base", "")
    just_entered = elapsed < 3600

    if mode == 21:
        return []

    if mode in (31, 32, 33):
        if mode == 33:
            series_key = cup_series_key
        else:
            series_key = MODE_TO_SERIES[mode]

        series_name = SERIES_NAMES.get(series_key, series_key)
        # hours elapsed = zero-indexed day; report one-indexed day
        # e.g., 3700s elapsed -> 3700//3600 = 1 -> Day 2
        series_day = (elapsed // 3600) + 1
        series_data = postseason.get(series_key, [])

        if just_entered:
            site_link = f"<{site_base}|{site_base.replace('https://', '')}>" if site_base else ""
            header_text = f"{cup_name}: {series_name} is starting now! {site_link}".strip()
            attachments = [_header_attachment(header_text)]
            if current_games:
                attachments.extend(format_current_games(current_games, site_base))
            return [{"text": header_text, "attachments": attachments}]

        messages = []

        # Yesterday's results: use day-based index (series_day - 2 for 0-indexed prior day)
        yesterday_idx = series_day - 2
        if series_data and 0 <= yesterday_idx < len(series_data):
            yesterday_games = series_data[yesterday_idx]
            header = f"{series_name} \u2014 Day {series_day - 1} Results"
            result_attachments = [_header_attachment(header)]
            for g in yesterday_games:
                result_attachments.append(format_matchup(g, site_base))

            today_pairs = set()
            if current_games:
                for g in current_games:
                    pair = tuple(sorted([g["team1Name"], g["team2Name"]]))
                    today_pairs.add(pair)

            for g in yesterday_games:
                pair = tuple(sorted([g["team1Name"], g["team2Name"]]))
                if pair not in today_pairs:
                    w1, l1, w2, l2 = updated_series_wl(g)
                    if w1 > w2:
                        winner, winner_wl = g["team1Name"], f"{w1}-{l1}"
                        loser, loser_wl = g["team2Name"], f"{w2}-{l2}"
                        winner_color = g.get("team1Color", "#62c462")
                    else:
                        winner, winner_wl = g["team2Name"], f"{w2}-{l2}"
                        loser, loser_wl = g["team1Name"], f"{w1}-{l1}"
                        winner_color = g.get("team2Color", "#62c462")
                    result_attachments.append(
                        _series_clinch_attachment(winner, winner_wl, loser, loser_wl, winner_color)
                    )

            messages.append({"text": header, "attachments": result_attachments})

        if current_games:
            header = f"{series_name} \u2014 Day {series_day} Games"
            upcoming_attachments = [_header_attachment(header)]
            upcoming_attachments.extend(format_current_games(current_games, site_base))
            messages.append({"text": header, "attachments": upcoming_attachments})

        return messages

    if mode == 22:
        if not just_entered:
            return []
        result = announce_series_outcome(postseason, "LDS", "Division Series")
        return [result] if result else []

    if mode == 23:
        if not just_entered:
            return []
        result = announce_series_outcome(postseason, "LCS", "Championship Series")
        return [result] if result else []

    if mode == 40:
        if not just_entered:
            return []
        result = announce_series_outcome(postseason, cup_series_key, cup_name)
        return [result] if result else []

    return []


def announce_series_outcome(postseason, series_key, series_name):
    """Build a styled message announcing the final outcome of a series."""
    series_data = postseason.get(series_key, [])
    if not series_data:
        return None

    last_day = series_data[-1]
    header = f"{series_name} Results"
    attachments = [_header_attachment(header)]

    for game in last_day:
        w1, l1, w2, l2 = updated_series_wl(game)
        if w1 > w2:
            winner, winner_wl = game["team1Name"], f"{w1}-{l1}"
            loser, loser_wl = game["team2Name"], f"{w2}-{l2}"
            winner_color = game.get("team1Color", "#62c462")
        else:
            winner, winner_wl = game["team2Name"], f"{w2}-{l2}"
            loser, loser_wl = game["team1Name"], f"{w1}-{l1}"
            winner_color = game.get("team2Color", "#62c462")
        attachments.append(
            _series_clinch_attachment(winner, winner_wl, loser, loser_wl, winner_color)
        )

    return {"text": header, "attachments": attachments}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(cup_key):
    token = os.getenv("SLACK_BOT_TOKEN")
    channel = os.getenv("SLACK_CHANNEL_ID")

    if not token or not channel:
        print("SLACK_BOT_TOKEN and SLACK_CHANNEL_ID must be set. Skipping.")
        return

    if cup_key not in CUPS:
        print(f"Unknown cup: {cup_key}. Must be 'star' or 'hellmouth'.")
        return

    cup = CUPS[cup_key]
    pacific_tz = pytz.timezone("America/Los_Angeles")
    now_pt = datetime.now(pacific_tz)
    print(f"[{now_pt.strftime('%Y-%m-%d %H:%M PT')}] Running {cup['cup_name']} notifier")

    weekday = now_pt.weekday()
    schedule = cup.get("schedule", {})
    if weekday not in schedule:
        print(f"  Not a {cup['cup_name']} day (weekday={weekday}). Skipping.")
        return

    day_config = schedule[weekday]
    start_hour = day_config["start_hour"]
    duration = day_config["duration"]
    end_hour = start_hour + duration

    if now_pt.hour < start_hour:
        print(f"  Too early (hour={now_pt.hour}, start={start_hour}). Skipping.")
        return

    if now_pt.hour >= end_hour:
        print(f"  Past window (hour={now_pt.hour}, end={end_hour}). Skipping.")
        return

    api_base = cup["api_base"]
    mode_data = fetch_json(f"{api_base}/mode")
    print(f"  Mode: {mode_data}")

    postseason = fetch_json(f"{api_base}/postseason")
    print(f"  Postseason series keys: {list(postseason.keys())}")

    current_games = fetch_json(f"{api_base}/currentGames")
    print(f"  Current games: {len(current_games)}")

    messages = build_notification(cup, mode_data, postseason, current_games)

    if messages:
        for i, msg in enumerate(messages, 1):
            text = msg["text"]
            attachments = msg.get("attachments")
            print(f"  Sending message {i}/{len(messages)}: {text[:80]}")
            send_slack_message(token, channel, text, cup["bot_username"], cup["bot_icon_url"], attachments)
            print(f"  Sent message {i}.")
    else:
        print("  No notification to send.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python notifier.py <star|hellmouth>")
        sys.exit(1)
    run(sys.argv[1])
