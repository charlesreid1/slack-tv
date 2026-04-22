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



def format_matchup(g, site_base=None):
    """Two-line hockey-bot style: bold name line (with game link), then abbr/score line."""
    if site_base:
        link = game_link(site_base, g)
        name_line = f"*{g['team1Name']} vs. {g['team2Name']}* | {link}"
    else:
        name_line = f"*{g['team1Name']} vs. {g['team2Name']}*"
    score_line = f"{g['team1Abbr']}: {g['team1Score']} | {g['team2Abbr']}: {g['team2Score']} | Final"
    return [name_line, score_line]


def game_link(site_base, game):
    game_id = game.get("id", "")
    desc = game.get("description", "")
    match = re.match(r"Game (\d+)", desc)
    label = f"Game {match.group(1)}" if match else "Watch"
    url = f"{site_base}/simulator/index.html?gameId={game_id}"
    return f"<{url}|{label}>"


def format_current_games(current_games, site_base=None):
    lines = []
    for g in sorted(current_games, key=lambda x: x.get("description", "")):
        w1, l1 = g["team1SeriesWinLoss"]
        w2, l2 = g["team2SeriesWinLoss"]
        t1 = f"{g['team1Name']} ({w1}-{l1})" if w1 or l1 else g["team1Name"]
        t2 = f"{g['team2Name']} ({w2}-{l2})" if w2 or l2 else g["team2Name"]
        if site_base:
            link = game_link(site_base, g)
            lines.append(f"{t1} vs. {t2}: {link}")
        else:
            lines.append(f"*{t1} vs. {t2}*")
    return lines


def build_notification(cup_config, mode_data, postseason, current_games=None):
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
        # e.g., 3700s elapsed → 3700//3600 = 1 → Day 2
        series_day = (elapsed // 3600) + 1
        series_data = postseason.get(series_key, [])

        if just_entered:
            site_link = f"<{site_base}|{site_base.replace('https://', '')}>" if site_base else ""
            lines = [f"{cup_name}: {series_name} is starting now! {site_link}".strip()]
            if current_games:
                lines.extend(format_current_games(current_games, site_base))
            return ["\n".join(lines)]

        messages = []

        # Yesterday's results: use day-based index (series_day - 2 for 0-indexed prior day)
        yesterday_idx = series_day - 2
        if series_data and 0 <= yesterday_idx < len(series_data):
            yesterday_games = series_data[yesterday_idx]
            outcome_lines = [f"*{series_name} — Day {series_day - 1} Results*"]
            for g in yesterday_games:
                outcome_lines.extend(format_matchup(g, site_base))

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
                    else:
                        winner, winner_wl = g["team2Name"], f"{w2}-{l2}"
                        loser, loser_wl = g["team1Name"], f"{w1}-{l1}"
                    outcome_lines.append(f"{winner} ({winner_wl}) wins the series over {loser} ({loser_wl})")

            messages.append("\n".join(outcome_lines))

        if current_games:
            upcoming_lines = [f"*{series_name} — Day {series_day} Games*"]
            upcoming_lines.extend(format_current_games(current_games, site_base))
            messages.append("\n".join(upcoming_lines))

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


def announce_series_outcome(postseason, series_key, series_name):
    series_data = postseason.get(series_key, [])
    if not series_data:
        return None

    last_day = series_data[-1]
    lines = [f"*{series_name} Results*"]
    for game in last_day:
        w1, l1, w2, l2 = updated_series_wl(game)
        if w1 > w2:
            winner, winner_wl = game["team1Name"], f"{w1}-{l1}"
            loser, loser_wl = game["team2Name"], f"{w2}-{l2}"
        else:
            winner, winner_wl = game["team2Name"], f"{w2}-{l2}"
            loser, loser_wl = game["team1Name"], f"{w1}-{l1}"
        lines.append(f"{winner} ({winner_wl}) defeats {loser} ({loser_wl})")
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
            print(f"  Sending message {i}/{len(messages)}: {msg[:80]}")
            send_slack_message(token, channel, msg, cup["bot_username"], cup["bot_icon_url"])
            print(f"  Sent message {i}.")
    else:
        print("  No notification to send.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python notifier.py <star|hellmouth>")
        sys.exit(1)
    run(sys.argv[1])
