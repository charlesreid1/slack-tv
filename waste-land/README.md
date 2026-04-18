# The Waste Land — Hourly Drip

Posts one line of T.S. Eliot's *The Waste Land* (1922) to a Slack channel every hour.

The poem is 434 lines. At one line per hour, it loops every ~18 days. Each line sits alone in the channel long enough to be read as a standalone fragment.

## How the line index works

Line selection is deterministic: `(unix_epoch_seconds // 3600) % total_lines`. This means:

- No state file needed — the script is stateless
- Any run at the same clock-hour produces the same line
- Manual reruns and retries are idempotent
- The sequence advances automatically across months and years

## Files

```
waste-land/
├── notifier.py       # The script
├── poem.txt          # The full text of the poem
├── icon.png          # Bot avatar (served via raw GitHub URL)
├── requirements.txt  # Python dependencies
└── README.md
```

## Running locally

```bash
cd waste-land
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
SLACK_BOT_TOKEN=xoxb-... SLACK_CHANNEL_ID=C012AB3CD python notifier.py
```
