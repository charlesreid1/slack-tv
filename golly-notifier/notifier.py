import os
import sys
import re
import requests
from datetime import datetime
import pytz

SLACK_API_URL = "https://slack.com/api/chat.postMessage"

CUPS = {
    "star": {
        "api_base": "https://cloud.star-vii.golly.life",
        "cup_name": "Star Cup",
        "cup_series_key": "SCS",
        "bot_username": "Star Cup",
        "bot_icon_url": "https://git.charlesreid1.com/charlesreid1/slack-tv/raw/branch/main/golly-notifier/icon-star.png",
        "days": [1, 2],  # Tuesday, Wednesday (weekday() values)
        "start_hour": 5,
    },
    "hellmouth": {
        "api_base": "https://cloud.vii.golly.life",
        "cup_name": "Hellmouth Cup",
        "cup_series_key": "HCS",
        "bot_username": "Hellmouth Cup",
        "bot_icon_url": "https://git.charlesreid1.com/charlesreid1/slack-tv/raw/branch/main/golly-notifier/icon-hellmouth.png",
        "days": [4, 5, 6],  # Friday, Saturday, Sunday
        "start_hour": 8,
    },
}

SERIES_NAMES = {
    "LDS": "Division Series",
    "LCS": "League Championship Series",
    "HCS": "Hellmouth VII Cup",
    "SCS": "Star Cup Series",
}

MODE_TO_SERIES = {
    31: "LDS",
    32: "LCS",
    33: None,  # filled per-cup: HCS or SCS
}


def fetch_json(url):
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


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



def format_matchup(g):
    """Two-line hockey-bot style: bold name line, then abbr/score line."""
    name_line = f"*{g['team1Name']} vs. {g['team2Name']}*"
    score_line = f"{g['team1Abbr']}: {g['team1Score']} | {g['team2Abbr']}: {g['team2Score']} | Final"
    return [name_line, score_line]


def format_current_games(current_games):
    lines = []
    for g in sorted(current_games, key=lambda x: x.get("description", "")):
        w1, l1 = g["team1SeriesWinLoss"]
        w2, l2 = g["team2SeriesWinLoss"]
        t1 = f"{g['team1Name']} ({w1}-{l1})" if w1 or l1 else g["team1Name"]
        t2 = f"{g['team2Name']} ({w2}-{l2})" if w2 or l2 else g["team2Name"]
        lines.append(f"*{t1} vs. {t2}*")
    return lines


def build_notification(cup_config, mode_data, postseason, current_games=None):
    mode = mode_data["mode"]
    elapsed = mode_data.get("elapsed", 0)
    cup_name = cup_config["cup_name"]
    cup_series_key = cup_config["cup_series_key"]
    just_entered = elapsed < 3600

    if mode == 21:
        return None

    if mode in (31, 32, 33):
        if not just_entered:
            return None

        if mode == 33:
            series_key = cup_series_key
        else:
            series_key = MODE_TO_SERIES[mode]

        series_name = SERIES_NAMES.get(series_key, series_key)
        series_day = (elapsed // 3600) + 1
        series_data = postseason.get(series_key, [])

        if series_day == 1:
            lines = [f"*{series_name} is starting now!*"]
            if current_games:
                lines.extend(format_current_games(current_games))
            return "\n".join(lines)

        if series_data:
            yesterday_games = series_data[-1]
            lines = [f"*{series_name} Update*"]
            for g in yesterday_games:
                w1, l1 = g["team1SeriesWinLoss"]
                w2, l2 = g["team2SeriesWinLoss"]
                lines.extend(format_matchup(g))
                lines.append(f"Series: {g['team1Name']} {w1}-{l1}, {g['team2Name']} {w2}-{l2}")
            return "\n".join(lines)

        return None

    if mode == 22:
        if not just_entered:
            return None
        return announce_series_outcome(postseason, "LDS", "Division Series")

    if mode == 23:
        if not just_entered:
            return None
        return announce_series_outcome(postseason, "LCS", "League Championship Series")

    if mode == 40:
        if not just_entered:
            return None
        return announce_series_outcome(postseason, cup_series_key, cup_name)

    return None


def announce_series_outcome(postseason, series_key, series_name):
    series_data = postseason.get(series_key, [])
    if not series_data:
        return None

    last_day = series_data[-1]
    lines = [f"*{series_name} Results*"]
    for game in last_day:
        w1, _ = game["team1SeriesWinLoss"]
        w2, _ = game["team2SeriesWinLoss"]
        if w1 > w2:
            winner = game["team1Name"]
            loser = game["team2Name"]
            series_wl = f"{w1}-{w2}"
        else:
            winner = game["team2Name"]
            loser = game["team1Name"]
            series_wl = f"{w2}-{w1}"
        lines.append(f"{winner} defeats {loser} ({series_wl})")
    return "\n".join(lines)


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
    if weekday not in cup["days"]:
        print(f"  Not a {cup['cup_name']} day (weekday={weekday}). Skipping.")
        return

    if now_pt.hour < cup["start_hour"]:
        print(f"  Too early (hour={now_pt.hour}, start={cup['start_hour']}). Skipping.")
        return

    api_base = cup["api_base"]
    mode_data = fetch_json(f"{api_base}/mode")
    print(f"  Mode: {mode_data}")

    postseason = fetch_json(f"{api_base}/postseason")
    print(f"  Postseason series keys: {list(postseason.keys())}")

    current_games = fetch_json(f"{api_base}/currentGames")
    print(f"  Current games: {len(current_games)}")

    message = build_notification(cup, mode_data, postseason, current_games)

    if message:
        print(f"  Sending: {message[:80]}")
        send_slack_message(token, channel, message, cup["bot_username"], cup["bot_icon_url"])
        print("  Sent.")
    else:
        print("  No notification to send.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python notifier.py <star|hellmouth>")
        sys.exit(1)
    run(sys.argv[1])
